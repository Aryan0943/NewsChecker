
import logging
import requests

from fastapi import APIRouter, HTTPException
from google.genai import errors as gemini_errors

from app.schemas import (
    ArticleRequest,
    AnalysisResponse,
    BiasResult,
    ClaimFactCheck,
    EvidenceSource,
    FactCheckResult,
)

from app.services.article_fetcher import extract_article_text
from app.services.text_preprocessor import preprocess_article
from app.services.claim_extractor import extract_claims_llm
from app.services.evidence_retriever import search_evidence
from app.services.source_analyzer import analyze_sources
from app.services.evidence_evaluator import evaluate_evidence
from app.services.bias_analyzer import analyze_bias, BIAS_CATEGORIES


router = APIRouter()
logger = logging.getLogger(__name__)


def get_pending_biases():
    return [
        {
            "category": category,
            "status": "pending",
            "score": None,
            "explanation": (
                "Bias analysis model has not been integrated yet."
            ),
        }
        for category in BIAS_CATEGORIES
    ]


def get_error_biases():
    return [
        {
            "category": category,
            "status": "error",
            "score": None,
            "explanation": "Bias analysis could not be completed.",
        }
        for category in BIAS_CATEGORIES
    ]


@router.post("/analyze", response_model=AnalysisResponse)
def analyze_article(request: ArticleRequest):

    article_url = request.content.strip()
    analysis_mode = request.analysis_mode

    # ==========================================
    # STEP 1: FETCH ARTICLE
    # ==========================================

    try:
        article = extract_article_text(article_url)

        content = preprocess_article(article["text"])
        article_title = article["title"]

    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail="The article website could not be reached.",
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    if not content:
        raise HTTPException(
            status_code=422,
            detail="No readable article content was extracted.",
        )

    # ==========================================
    # STEP 2: INITIALIZE RESULTS
    # ==========================================

    fact_check_result = FactCheckResult()
    bias_results = []

    # ==========================================
    # STEP 3: BIAS ANALYSIS
    # ==========================================

    if analysis_mode in ("bias", "both"):

        try:
            raw_bias_results = analyze_bias(
                article_text=content,
                article_title=article_title,
            )

            bias_results = [
                BiasResult(**result)
                for result in raw_bias_results
            ]

        except Exception:
            logger.exception("Bias analysis failed.")
            bias_results = [
                BiasResult(**result)
                for result in get_error_biases()
            ]

    # ==========================================
    # STEP 4: FACT-CHECKING
    # ==========================================

    if analysis_mode in ("fact", "both"):

        # --------------------------------------
        # 4A. Extract claims
        # --------------------------------------

        try:
            extracted_claims = extract_claims_llm(
                article_text=content,
                article_title=article_title,
                publish_date=article.get("publish_date"),
                max_claims=5,
            )

        except gemini_errors.APIError as exc:
            logger.exception("Gemini claim extraction failed.")

            raise HTTPException(
                status_code=502,
                detail=(
                    "Gemini is temporarily unavailable during "
                    "claim extraction. Please try again."
                ),
            ) from exc

        except Exception as exc:
            logger.exception("Unexpected claim extraction error.")

            raise HTTPException(
                status_code=500,
                detail="An error occurred during claim extraction.",
            ) from exc

        # --------------------------------------
        # 4B. Filter eligible claims
        # --------------------------------------

        print("\n========== GEMINI API DEBUG ==========")
        print("Article:", article_title)
        print("Total extracted claims:", len(extracted_claims))

        for index, claim in enumerate(extracted_claims, start=1):
            print(f"\nClaim {index}: {claim.claim_text}")
            print("Type:", claim.claim_type)
            print("Centrality:", claim.centrality)
            print("Checkable:", claim.checkable)
            print("Grounding status:", claim.grounding_status)
            print("Entities:", claim.entities)
            print("Numbers:", claim.numbers)

        claims = [
            claim
            for claim in extracted_claims
            if (
                claim.checkable
                and claim.grounding_status in {
                    "grounded",
                    "needs_review",
                }
                and claim.source_sentence
                and claim.claim_text
            )
        ]

        print("\nClaims passed to fact checker:", len(claims))
        print("======================================\n")

        # --------------------------------------
        # 4C. Retrieve and evaluate evidence
        # --------------------------------------

        claim_results = []

        try:
            for index, claim_obj in enumerate(claims, start=1):

                claim_text = claim_obj.claim_text

                print(
                    f"\nFact-checking claim {index}/{len(claims)}:"
                )
                print(claim_text)

                evidence = search_evidence(
                    claim=claim_text,
                    max_results=5,
                    context=article_title or "",
                )

                print(
                    "Evidence sources retrieved:",
                    len(evidence) if evidence else 0,
                )

                source_analysis = analyze_sources(
                    evidence,
                    original_article_url=article_url,
                )

                evaluation = evaluate_evidence(
                    claim=claim_text,
                    evidence=source_analysis["sources"],
                    source_analysis=source_analysis,
                )

                limitations = list(
                    evaluation.get("limitations", [])
                )

                if claim_obj.grounding_status == "needs_review":
                    limitations.append(
                        "Article grounding could not be completed. "
                        "This claim is provisional and its connection "
                        "to the original article requires review."
                    )

                claim_result = ClaimFactCheck(
                    claim=evaluation["claim"],
                    verdict=evaluation["verdict"],
                    confidence=(
                        "low"
                        if claim_obj.grounding_status == "needs_review"
                        else evaluation["confidence"]
                    ),
                    explanation=evaluation["explanation"],
                    supporting_sources=[
                        EvidenceSource(**source)
                        for source in evaluation.get(
                            "supporting_sources", []
                        )
                    ],
                    contradicting_sources=[
                        EvidenceSource(**source)
                        for source in evaluation.get(
                            "contradicting_sources", []
                        )
                    ],
                    limitations=limitations,
                )

                claim_results.append(claim_result)

                print("Verdict:", claim_result.verdict)

        except (
            gemini_errors.APIError,
            RuntimeError,
            ValueError,
        ) as exc:
            logger.exception("Evidence pipeline error.")

            raise HTTPException(
                status_code=502,
                detail=(
                    "Evidence retrieval or Gemini evaluation failed. "
                    "Please try again."
                ),
            ) from exc

        except Exception as exc:
            logger.exception("Unexpected fact-checking error.")

            raise HTTPException(
                status_code=500,
                detail=(
                    "An unexpected error occurred during fact-checking."
                ),
            ) from exc

        # --------------------------------------
        # 4D. Calculate overall verdict
        # --------------------------------------

        verdicts = [
            result.verdict
            for result in claim_results
        ]

        supported_count = verdicts.count("supported")
        contradicted_count = verdicts.count("contradicted")
        mixed_count = verdicts.count("mixed")
        insufficient_count = verdicts.count("insufficient_evidence")

        if not claim_results:
            overall_status = "unverified"
            summary = (
                "No claims passed the article-grounding "
                "and checkability checks."
            )

        else:
            if contradicted_count > 0 and supported_count > 0:
                overall_status = "mixed"

            elif contradicted_count > 0:
                overall_status = "disputed"

            elif supported_count == len(verdicts):
                overall_status = "claims_supported"

            else:
                overall_status = "unverified"

            summary = (
                f"Evaluated {len(claim_results)} claims: "
                f"{supported_count} supported, "
                f"{contradicted_count} contradicted, "
                f"{mixed_count} mixed, and "
                f"{insufficient_count} with insufficient evidence."
            )

        # --------------------------------------
        # 4E. Collect sources
        # --------------------------------------

        source_strings = []

        for result in claim_results:
            for source in (
                result.supporting_sources
                + result.contradicting_sources
            ):
                source_strings.append(
                    f"Claim: {result.claim}\n"
                    f"Source: {source.title}\n"
                    f"URL: {source.url}\n"
                    f"Evidence: {source.excerpt}"
                )

        fact_check_result = FactCheckResult(
            status=overall_status,
            summary=summary,
            sources=source_strings,
            claims=claim_results,
        )

    # ==========================================
    # STEP 5: GENERATE RESPONSE MESSAGE
    # ==========================================

    if analysis_mode == "fact":
        message = (
            "Article fetched successfully. "
            "Fact-checking analysis completed."
        )

    elif analysis_mode == "bias":
        message = (
            "Article fetched successfully. "
            "Bias analysis requested. "
            "The analysis model is currently under development."
        )

    else:
        message = (
            "Article fetched successfully. "
            "Both fact-checking and bias analysis were requested."
        )

    # ==========================================
    # STEP 6: RETURN FINAL RESPONSE
    # ==========================================

    return AnalysisResponse(
        mode="url",
        analysis_mode=analysis_mode,
        article_title=article_title,
        article_text=content,
        biases=bias_results,
        fact_check=fact_check_result,
        message=message,
    )

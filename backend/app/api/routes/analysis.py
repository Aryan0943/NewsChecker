
import requests

from fastapi import APIRouter, HTTPException
from google.genai import errors as gemini_errors

from app.schemas import (
    ArticleRequest,
    AnalysisResponse,
    ClaimFactCheck,
    EvidenceSource,
)

from app.services.article_fetcher import extract_article_text
from app.services.text_preprocessor import preprocess_article
from app.services.claim_extractor import extract_claims_llm
from app.services.evidence_retriever import search_evidence
from app.services.source_analyzer import analyze_sources
from app.services.evidence_evaluator import evaluate_evidence


router = APIRouter()


def get_pending_biases():
    return [
        {"category": "political", "status": "pending"},
        {"category": "gender", "status": "pending"},
        {"category": "communal/caste", "status": "pending"},
        {"category": "cultural", "status": "pending"},
    ]


@router.post("/analyze", response_model=AnalysisResponse)
def analyze_article(request: ArticleRequest):

    article_url = request.content.strip()

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
    # STEP 2: EXTRACT CLAIMS USING GEMINI
    # ==========================================

    try:
        extracted_claims = extract_claims_llm(
            article_text=content,
            article_title=article_title,
            publish_date=article.get("publish_date"),
            max_claims=5,
        )

    except gemini_errors.APIError as exc:
        print("Gemini claim extraction failed:", exc)

        raise HTTPException(
            status_code=502,
            detail=(
                "Gemini is temporarily unavailable during "
                "claim extraction. Please try again."
            ),
        ) from exc

    except Exception as exc:
        print("Unexpected claim extraction error:", repr(exc))

        raise HTTPException(
            status_code=500,
            detail="An error occurred during claim extraction.",
        ) from exc

    # ==========================================
    # STEP 3: DEBUG AND FILTER CLAIMS
    # ==========================================

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

    # Allow grounded claims and provisional claims.
    # Rejected claims must never enter fact-checking.

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

    if not claims:
        return AnalysisResponse(
            mode="url",
            article_title=article_title,
            article_text=content,
            biases=get_pending_biases(),
            fact_check={
                "status": "unverified",
                "summary": (
                    "No claims passed the article-grounding "
                    "and checkability checks."
                ),
                "sources": [],
                "claims": [],
            },
            message=(
                "The article was fetched, but no eligible "
                "grounded claims were available for fact-checking."
            ),
        )

    # ==========================================
    # STEP 4: RETRIEVE AND EVALUATE EVIDENCE
    # ==========================================

    claim_results = []

    try:
        for index, claim_obj in enumerate(claims, start=1):

            claim_text = claim_obj.claim_text

            print(
                f"\nFact-checking claim {index}/{len(claims)}:"
            )
            print(claim_text)

            # Retrieve external evidence.
            evidence = search_evidence(
                claim=claim_text,
                max_results=5,
                context=article_title or "",
            )

            print(
                "Evidence sources retrieved:",
                len(evidence) if evidence else 0,
            )

            # Analyse source relationships.
            source_analysis = analyze_sources(
                evidence,
                original_article_url=article_url
            )

            # Evaluate evidence using Gemini.
            evaluation = evaluate_evidence(
                claim=claim_text,
                evidence=source_analysis["sources"],
                source_analysis=source_analysis,
            )

            # Preserve limitations from evidence evaluation.
            limitations = list(
                evaluation.get("limitations", [])
            )

            # Record incomplete article grounding.
            if claim_obj.grounding_status == "needs_review":
                limitations.append(
                    "Article grounding could not be completed. "
                    "This claim is provisional and its connection "
                    "to the original article requires review."
                )

            # Convert evaluation into a Pydantic model.
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

    except (gemini_errors.APIError, RuntimeError, ValueError) as exc:
        print("Evidence pipeline error:", repr(exc))

        raise HTTPException(
            status_code=502,
            detail=(
                "Evidence retrieval or Gemini evaluation failed. "
                "Please try again."
            ),
        ) from exc

    except Exception as exc:
        print("Unexpected fact-checking error:", repr(exc))

        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during fact-checking.",
        ) from exc

    # ==========================================
    # STEP 5: CALCULATE OVERALL VERDICT
    # ==========================================

    verdicts = [
        result.verdict
        for result in claim_results
    ]

    supported_count = verdicts.count("supported")
    contradicted_count = verdicts.count("contradicted")
    mixed_count = verdicts.count("mixed")
    insufficient_count = verdicts.count("insufficient_evidence")

    if contradicted_count > 0 and supported_count > 0:
        overall_status = "mixed"

    elif contradicted_count > 0:
        overall_status = "disputed"

    elif supported_count == len(verdicts):
        overall_status = "claims_supported"

    else:
        overall_status = "unverified"

    # ==========================================
    # STEP 6: GENERATE SUMMARY
    # ==========================================

    summary = (
        f"Evaluated {len(claim_results)} claims: "
        f"{supported_count} supported, "
        f"{contradicted_count} contradicted, "
        f"{mixed_count} mixed, and "
        f"{insufficient_count} with insufficient evidence."
    )

    # ==========================================
    # STEP 7: COLLECT SOURCES
    # ==========================================

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

    # ==========================================
    # STEP 8: RETURN FINAL RESPONSE
    # ==========================================

    return AnalysisResponse(
        mode="url",
        article_title=article_title,
        article_text=content,
        biases=get_pending_biases(),
        fact_check={
            "status": overall_status,
            "summary": summary,
            "sources": source_strings,
            "claims": claim_results,
        },
        message=(
            "Article fetched successfully. Claims were extracted "
            "and evaluated against retrieved external evidence."
        ),
    )

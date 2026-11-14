
import unicodedata
import re
import json
import logging
import time
from pydantic import ValidationError

from app.services.claim_models import Claim
from app.services.evidence_evaluator import (
    get_gemini_client,
    GEMINI_MODEL,
)
from app.services.fact_check import extract_claims


logger = logging.getLogger(__name__)


# ============================================================
# 1. TEXT NORMALIZATION
# ============================================================

def normalize_text(text: str) -> str:
    """
    Normalize harmless formatting differences while
    preserving the words, numbers, and their order.
    """
    text = unicodedata.normalize("NFKC", text or "")

    translations = str.maketrans({
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u00a0": " ",
    })

    text = text.translate(translations)

    # Ignore spaces around punctuation.
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()
# ============================================================
# 2. CLAIM GROUNDING VALIDATION
# ============================================================

def validate_claim_grounding(
    claim: Claim,
    article_text: str,
    article_title: str = "",
) -> Claim:
    """
    Check whether extracted entities and numerical values
    appear in the article title or body.

    This is a preliminary metadata check, not full semantic
    verification of the claim.
    """

    context = f"{article_title}\n{article_text}"

    # Normalize punctuation and whitespace.
    normalized_context = re.sub(
        r"[^a-z0-9]+",
        " ",
        context.lower(),
    )

    issues = []

    # --------------------------------------------------------
    # Check entities
    # --------------------------------------------------------

    for entity in claim.entities:

        normalized_entity = re.sub(
            r"[^a-z0-9]+",
            " ",
            entity.lower(),
        ).strip()

        if (
            normalized_entity
            and normalized_entity not in normalized_context
        ):
            issues.append(
                f"Entity '{entity}' was not found in the article."
            )

    # --------------------------------------------------------
    # Check numerical values
    # --------------------------------------------------------

    # Normalize thousands separators in the article.
    numeric_context = re.sub(
        r"(?<=\d),(?=\d)",
        "",
        context,
    )

    for number in claim.numbers:

        match = re.search(
            r"\d+(?:\.\d+)?",
            number,
        )

        if not match:
            continue

        # Also normalize commas in Gemini's extracted number.
        numeric_value = match.group().replace(",", "")

        if not re.search(
            r"(?<!\d)"
            + re.escape(numeric_value)
            + r"(?!\d)",
            numeric_context,
        ):
            issues.append(
                f"Number '{number}' was not found in the article."
            )

    # --------------------------------------------------------
    # Set grounding status
    # --------------------------------------------------------

    if issues:

        claim.grounding_status = "needs_review"

        claim.validation_notes = " ".join(issues)

    else:

        claim.grounding_status = "grounded"

        claim.validation_notes = (
            "Extracted entities and numerical values "
            "were found in the article context."
        )

    return claim


def validate_claims_semantically(
    claims: list[Claim],
    article_text: str,
    article_title: str = "",
) -> list[Claim]:
    """
    Use Gemini to check whether each complete claim
    is supported by the article context.

    This checks article-to-claim consistency, not truth.
    """

    if not claims:
        return []

    prompt_claims = [
        {
            "claim_id": claim.claim_id,
            "source_sentence": claim.source_sentence,
            "claim_text": claim.claim_text,
            "claim_type": claim.claim_type,
        }
        for claim in claims
    ]

    prompt = f"""
You are a conservative semantic claim-grounding validator.

Your task is to determine whether each extracted claim
is supported by the supplied news article.

ARTICLE TITLE:
{article_title}

ARTICLE TEXT:
{article_text[:18000]}

CLAIMS TO VALIDATE:
{json.dumps(prompt_claims, ensure_ascii=False)}

For EACH claim, assess whether its complete meaning is
supported by the article title or article body.

Use these statuses:

- grounded:
  The article explicitly supports the complete claim.
  Contextual rewriting is allowed if it does not change meaning.

- needs_review:
  The article provides partial or ambiguous support,
  or the claim contains details that cannot be confidently
  linked to the relevant subject or event.

- rejected:
  The claim contradicts the article or adds unsupported
  material facts, changes the result, or changes attribution.

IMPORTANT RULES:

1. Do not use outside knowledge.
2. Do not decide whether the article itself is true.
3. Finding the same name or number somewhere in the article
   is not sufficient.
4. Check whether numbers belong to the correct person,
   event, measurement or reporting period.
5. Preserve attribution: a reported statement must remain
   attributed to its speaker.
6. Preserve uncertainty, allegations and predictions.
7. Do not convert an arrest into a conviction.
8. Do not convert correlation into causation.
9. Do not treat a study's limited findings as universal facts.
10. The original sentence may be supplemented by other
    article context, including the headline.
11. If evidence is ambiguous, choose needs_review.
12. Return an assessment for every supplied claim ID.

13. Preserve the main factual finding of the source_sentence.
    Do not replace the central finding with background information,
    such as the discovery location, identity or historical context.

14. The claim_text must represent the actual factual assertion
    made in its source_sentence. You may use other article context
    to resolve references, but must not substitute a different fact.

15. Preserve attribution whenever the source_sentence attributes
    information to a researcher, study, institution, official,
    witness or publication.

16. Distinguish between:
    - A researcher conducting or reporting a study.
    - A study finding or suggesting something.
    - A journalist reporting that finding.
    Do not present an attributed finding as independently verified fact.

17. For scientific claims, preserve important measurements,
    comparisons, experimental findings and scientific qualifications.
    Do not remove details that make the finding meaningful.

18. Preserve uncertainty and precision. Words such as
    "approximately", "roughly", "may", "could", "suggests",
    "appears" and "is associated with" must not be converted
    into stronger conclusions.

19. Do not add attribution to a person or organization unless
    the article supports that attribution.

20. If a source_sentence contains multiple factual assertions,
    prioritize its central independently checkable finding.
    Do not combine unrelated assertions into one claim.


Return ONLY valid JSON:

{{
    "assessments": [
        {{
            "claim_id": "C1",
            "status": "grounded",
            "notes": "The article explicitly supports the claim."
        }}
    ]
}}
"""

    client = None

    try:
        client = get_gemini_client()

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config={
                "response_mime_type": "application/json"
            },
        )

        if not response.text:
            raise ValueError(
                "Gemini returned an empty grounding response."
            )

        result = json.loads(response.text)

        assessments = result.get("assessments")

        if not isinstance(assessments, list):
            raise ValueError(
                "Invalid semantic grounding response."
            )

        # Only accept assessments for known claim IDs.
        assessment_map = {}

        valid_statuses = {
            "grounded",
            "needs_review",
            "rejected",
        }

        for item in assessments:

            if not isinstance(item, dict):
                continue

            claim_id = item.get("claim_id")
            status = item.get("status")

            if (
                isinstance(claim_id, str)
                and status in valid_statuses
                and claim_id not in assessment_map
            ):
                assessment_map[claim_id] = item

        for claim in claims:

            assessment = assessment_map.get(claim.claim_id)

            if assessment is None:
                claim.grounding_status = "needs_review"
                claim.validation_notes = (
                    "No valid semantic grounding assessment "
                    "was returned."
                )
                continue

            claim.grounding_status = assessment["status"]

            claim.validation_notes = str(
                assessment.get("notes") or
                "No explanation provided."
            )

        return claims

    except Exception:

        logger.exception(
            "Semantic claim grounding failed."
        )

        # Fail safely: never treat unvalidated claims
        # as semantically grounded.
        for claim in claims:
            claim.grounding_status = "needs_review"
            claim.validation_notes = (
                "Semantic validation could not be completed."
            )

        return claims

    finally:

        if client is not None:
            try:
                client.close()
            except Exception:
                logger.exception(
                    "Failed to close Gemini grounding client."
                )

# ============================================================
# 3. FALLBACK CLAIM FILTERING
# ============================================================

def filter_fallback_claims(
    raw_claims: list[str],
) -> list[str]:
    """Remove promotional, opinion-based and irrelevant sentences."""

    rejected_phrases = [
        "cements its position",
        "global powerhouse",
        "aspirations of its farmers",
        "next frontier of growth",
        "emerging opportunities",
        "will not just motivate",
        "path to viksit bharat",
        "subscribe",
        "advertisement",
        "photo credit",
        "read more",
    ]

    accepted = []

    for sentence in raw_claims:

        sentence = sentence.strip()

        if len(sentence) < 35:
            continue

        lowered = sentence.lower()

        if any(
            phrase in lowered
            for phrase in rejected_phrases
        ):
            continue

        if sentence not in accepted:
            accepted.append(sentence)

    return accepted


# ============================================================
# 4. GEMINI-BASED CLAIM EXTRACTION
# ============================================================

def extract_claims_llm(
    article_text: str,
    article_title: str = "",
    publish_date: str | None = None,
    max_claims: int = 5,
) -> list[Claim]:
    """
    Extract important, independently verifiable claims
    from a news article using Gemini.

    Validates original sentence provenance and extracted
    entities/numbers.

    Falls back to rule-based extraction if Gemini fails.
    """

    if not article_text or not article_text.strip():
        return []

    article_text = article_text.strip()

    prompt = f"""
You are a professional fact-checking claim extraction system.

Your task is to extract important factual claims from a news article.

ARTICLE TITLE:
{article_title},

PUBLICATION DATE:
{publish_date or "Unknown"}
*
ARTICLE TEXT:
{article_text[:18000]}

Extract at most {max_claims} important, independently verifiable claims.

RULES:

1. Extract factual claims, not opinions or recommendations.

2. Preserve forecasts and expectations as reported expectations
   when they are important and independently checkable.
   Never convert them into confirmed outcomes.

3. Prioritize claims central to the article.

4. Each source_sentence MUST be copied word-for-word
   from the article.

5. claim_text should be understandable independently,
   without needing the surrounding article.

6. You may add context from the title or article to make
   a sentence understandable, but MUST NOT invent facts.

7. Preserve the difference between:
   - Someone making a statement.
   - The statement itself being true.

8. Preserve exact numbers, dates, locations and entities.

9. Do not convert uncertainty into certainty.

10. Avoid duplicate claims.

11. Every detail in claim_text must be supported by
    the article title or article body.

12. Do not introduce a person's name, location, number,
    date or event unless it is supported by the article.

CLAIM TYPES:

- event
- reported_statement
- statistic
- historical
- scientific
- political
- other

CENTRALITY:

- high: central to the headline or main story
- medium: important supporting information
- low: minor information

Return ONLY valid JSON in this format:

{{
    "claims": [
        {{
            "claim_id": "C1",
            "source_sentence": "Exact sentence from article.",
            "claim_text": "Standalone factual claim.",
            "claim_type": "event",
            "entities": ["Entity 1"],
            "location": "Location or null",
            "time_reference": "Time or null",
            "numbers": ["50"],
            "centrality": "high",
            "checkable": true
        }}
    ]
}}

If there are no checkable claims, return:

{{
    "claims": []
}}

Do not include Markdown outside the JSON.
"""

    client = None

    try:

        # ----------------------------------------------------
        # Call Gemini
        # ----------------------------------------------------

        client = get_gemini_client()

        
        response = None

        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json"
                    },
                )
                break

            except Exception as error:
                if attempt == 2:
                    raise

                logger.warning(
                    "Gemini extraction attempt %s failed: %s. Retrying...",
                    attempt + 1,
                    error,
                )

                time.sleep(2 ** (attempt + 1))


        if not response.text:
            raise ValueError(
                "Gemini returned an empty response."
            )

        result = json.loads(response.text)

        if not isinstance(result, dict):
            raise ValueError(
                "Gemini response must be a JSON object."
            )

        raw_claims = result.get("claims")

        if not isinstance(raw_claims, list):
            raise ValueError(
                "Gemini did not return a claims list."
            )

        normalized_article = normalize_text(article_text)

        validated_claims = []

        # ----------------------------------------------------
        # Validate individual claims
        # ----------------------------------------------------

        for item in raw_claims[:max_claims]:

            if not isinstance(item, dict):
                continue

            source_sentence = item.get(
                "source_sentence",
                "",
            )

            # Original sentence must exist in article text.
            if (
                not isinstance(source_sentence, str)
                or normalize_text(source_sentence)
                not in normalized_article
            ):

                logger.warning(
                    "Rejected unmatched source sentence: %r",
                    source_sentence[:250],
                )

                continue

            try:

                claim = Claim.model_validate(item)

            except ValidationError:

                logger.warning(
                    "Rejected an invalid claim object."
                )

                continue

            if not claim.checkable:
                continue

            if not claim.claim_text.strip():
                continue

            # Validate entities and numbers against
            # the headline and complete article.
            
            claim = validate_claim_grounding(
                claim=claim,
                article_text=article_text,
                article_title=article_title,
            )

            # Fallback claims are not semantically verified.
            validated_claims.append(claim)


        # ----------------------------------------------------
        # Remove duplicate claim IDs
        # ----------------------------------------------------

        seen_ids = set()
        unique_claims = []

        for claim in validated_claims:

            if claim.claim_id in seen_ids:
                continue

            seen_ids.add(claim.claim_id)
            unique_claims.append(claim)

        if unique_claims:
            return validate_claims_semantically(
                claims=unique_claims,
                article_text=article_text,
                article_title=article_title,
            )

        logger.warning(
            "Gemini returned no valid claims. Using fallback."
        )

    except Exception as error:

        logger.exception(
            "Gemini claim extraction failed: %s",
            error,
        )

    finally:

        if client is not None:

            try:
                client.close()

            except Exception:
                logger.exception(
                    "Failed to close Gemini client."
                )

    # ========================================================
    # 5. RULE-BASED FALLBACK
    # ========================================================

    try:

        raw_claims = extract_claims(
            article_text,
            max_claims=20,
        )

        fallback_claims = filter_fallback_claims(
            raw_claims
        )

        results = []

        for index, sentence in enumerate(
            fallback_claims[:max_claims],
            start=1,
        ):

            claim = Claim(
                claim_id=f"F{index}",
                source_sentence=sentence,
                claim_text=sentence,
                claim_type="other",
                centrality="medium",
                checkable=True,
            )

            claim = validate_claim_grounding(
                claim=claim,
                article_text=article_text,
                article_title=article_title,
            )

            claim.grounding_status = "needs_review"
            claim.validation_notes = (
                "Extracted using rule-based fallback. "
                "Entity and numerical checks are preliminary only. "
                "Semantic validation has not been completed."
            )

            results.append(claim)

        return results

    except Exception:

        logger.exception(
            "Rule-based claim extraction also failed."
        )

        return []

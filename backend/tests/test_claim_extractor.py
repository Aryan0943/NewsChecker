
from unittest.mock import patch

from app.services.claim_extractor import (
    normalize_text,
    extract_claims_llm,
)


def test_normalize_text():
    assert normalize_text(
        "Police   arrested\n protesters."
    ) == "Police arrested protesters."


def test_empty_article():
    assert extract_claims_llm("") == []


@patch("app.services.claim_extractor.get_gemini_client")
@patch("app.services.claim_extractor.extract_claims")
def test_fallback_when_gemini_fails(
    mock_fallback,
    mock_client,
):
    mock_client.side_effect = RuntimeError(
        "Gemini unavailable"
    )

    mock_fallback.return_value = [
        "Police arrested several protesters."
    ]

    claims = extract_claims_llm(
        article_text="Police arrested several protesters."
    )

    assert len(claims) == 1
    assert claims[0].claim_id == "F1"
    assert claims[0].source_sentence == (
        "Police arrested several protesters."
    )

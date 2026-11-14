
from types import SimpleNamespace

import pytest

from app.api.routes import analysis
from app.schemas import ArticleRequest


def make_claim(number):
    return SimpleNamespace(
        claim_text=f"Test claim {number}",
        claim_type="factual",
        centrality="high",
        checkable=True,
        grounding_status="grounded",
        source_sentence=f"Test source sentence {number}",
        entities=[],
        numbers=[],
    )


def test_one_claim_failure_does_not_stop_remaining_claims(monkeypatch):
    # Mock article fetching and preprocessing
    monkeypatch.setattr(
        analysis,
        "extract_article_text",
        lambda url: {
            "text": "This is a test article with five factual claims.",
            "title": "Test Article",
            "publish_date": "2026-11-14",
        },
    )

    monkeypatch.setattr(
        analysis,
        "preprocess_article",
        lambda text: text,
    )

    # Simulate five successfully extracted claims
    monkeypatch.setattr(
        analysis,
        "extract_claims_llm",
        lambda **kwargs: [
            make_claim(i) for i in range(1, 6)
        ],
    )

    # Mock evidence retrieval and source analysis
    monkeypatch.setattr(
        analysis,
        "search_evidence",
        lambda **kwargs: [
            {
                "title": "Test Source",
                "domain": "example.com",
                "url": "https://example.com/source",
                "content": "Test evidence content.",
            }
        ],
    )

    monkeypatch.setattr(
        analysis,
        "analyze_sources",
        lambda evidence, original_article_url: {
            "sources": evidence,
            "similarity_groups": [],
            "attribution_relationships": [],
            "independent_group_count": 2,
            "independence_assessment": "independent",
        },
    )

    # Simulate successful evaluations and one failure
    evaluations = {
        "Test claim 1": "supported",
        "Test claim 2": "supported",
        "Test claim 4": "contradicted",
        "Test claim 5": "supported",
    }

    def mock_evaluate_evidence(claim, evidence, source_analysis):
        if claim == "Test claim 3":
            raise RuntimeError("Simulated Gemini API failure")

        return {
            "claim": claim,
            "verdict": evaluations[claim],
            "confidence": "high",
            "explanation": "Simulated test evaluation.",
            "supporting_sources": (
                [{"title": "Test Source",
                  "domain": "example.com",
                  "url": "https://example.com/source",
                  "excerpt": "Test evidence content."}]
                if evaluations[claim] == "supported"
                else []
            ),
            "contradicting_sources": (
                [{"title": "Test Source",
                  "domain": "example.com",
                  "url": "https://example.com/source",
                  "excerpt": "Test evidence content."}]
                if evaluations[claim] == "contradicted"
                else []
            ),
            "limitations": [],
        }

    monkeypatch.setattr(
        analysis,
        "evaluate_evidence",
        mock_evaluate_evidence,
    )

    # Execute the actual API route function
    request = ArticleRequest(
        content="https://example.com/article",
        analysis_mode="fact",
    )

    response = analysis.analyze_article(request)

    # Verify all five claims are returned
    assert len(response.fact_check.claims) == 5

    # Verify the successful claims retain their verdicts
    assert response.fact_check.claims[0].verdict == "supported"
    assert response.fact_check.claims[1].verdict == "supported"

    # Verify the failed claim is handled safely
    failed_claim = response.fact_check.claims[2]

    assert failed_claim.verdict == "insufficient_evidence"
    assert failed_claim.confidence == "low"
    assert "RuntimeError" in " ".join(failed_claim.limitations)

    # Verify processing continued after the failure
    assert response.fact_check.claims[3].verdict == "contradicted"
    assert response.fact_check.claims[4].verdict == "supported"


import json
import pytest

from app.services import evidence_evaluator


CLAIM = "The government announced a new railway project."

EVIDENCE = [
    {
        "title": "Railway project announced",
        "domain": "example.com",
        "url": "https://example.com/news",
        "published_date": "2026-11-18",
        "content": "The government announced a new railway project."
    }
]


# Mock Gemini client
class MockClient:
    def close(self):
        pass


# Initial evaluator response
def initial_response(verdict="supported"):
    return {
        "verdict": verdict,
        "confidence": "high",
        "explanation": "The evidence was evaluated.",
        "supporting_evidence": [
            {
                "source_id": "S1",
                "excerpt": "The government announced a new railway project."
            }
        ],
        "contradicting_evidence": [],
        "limitations": []
    }


# Set up the initial Gemini evaluator call
def setup_evaluator(monkeypatch, verdict="supported"):

    response = initial_response(verdict)

    monkeypatch.setattr(
        evidence_evaluator,
        "get_gemini_client",
        lambda: MockClient()
    )

    monkeypatch.setattr(
        evidence_evaluator,
        "generate_with_retry",
        lambda client, prompt, model=None: json.dumps(response)
    )


# TEST 1: Verified supporting evidence
def test_integration_supports_claim(monkeypatch):

    setup_evaluator(monkeypatch)

    monkeypatch.setattr(
        evidence_evaluator,
        "verify_evidence_semantics",
        lambda claim, evidence_items, today_date=None: [
            {
                "evidence_id": "E1",
                "relationship": "supports",
                "explanation": "Evidence directly supports the claim."
            }
        ]
    )

    result = evidence_evaluator.evaluate_evidence(
        CLAIM,
        EVIDENCE
    )

    assert result["verdict"] == "supported"
    assert len(result["supporting_sources"]) == 1
    assert result["confidence"] == "high"


# TEST 2: Evidence actually contradicts the claim
def test_integration_changes_verdict_to_contradicted(monkeypatch):

    setup_evaluator(monkeypatch, verdict="supported")

    monkeypatch.setattr(
        evidence_evaluator,
        "verify_evidence_semantics",
        lambda claim, evidence_items, today_date=None: [
            {
                "evidence_id": "E1",
                "relationship": "contradicts",
                "explanation": "Evidence contradicts the claim."
            }
        ]
    )

    result = evidence_evaluator.evaluate_evidence(
        CLAIM,
        EVIDENCE
    )

    assert result["verdict"] == "contradicted"
    assert len(result["supporting_sources"]) == 0
    assert len(result["contradicting_sources"]) == 1


# TEST 3: Evidence is unrelated
def test_integration_unrelated_evidence(monkeypatch):

    setup_evaluator(monkeypatch)

    monkeypatch.setattr(
        evidence_evaluator,
        "verify_evidence_semantics",
        lambda claim, evidence_items, today_date=None: [
            {
                "evidence_id": "E1",
                "relationship": "unrelated",
                "explanation": "Evidence is unrelated."
            }
        ]
    )

    result = evidence_evaluator.evaluate_evidence(
        CLAIM,
        EVIDENCE
    )

    assert result["verdict"] == "insufficient_evidence"
    assert len(result["supporting_sources"]) == 0
    assert result["confidence"] == "low"


# TEST 4: Semantic verifier fails
def test_integration_verifier_failure_preserves_original_verdict(
    monkeypatch
):

    setup_evaluator(monkeypatch, verdict="supported")

    def fail_verifier(*args, **kwargs):
        raise RuntimeError("Verifier unavailable")

    monkeypatch.setattr(
        evidence_evaluator,
        "verify_evidence_semantics",
        fail_verifier
    )

    result = evidence_evaluator.evaluate_evidence(
        CLAIM,
        EVIDENCE
    )

    assert result["verdict"] == "supported"
    assert result["confidence"] == "low"
    assert len(result["supporting_sources"]) == 1

    assert any(
        "Semantic verification could not be completed"
        in limitation
        for limitation in result["limitations"]
    )

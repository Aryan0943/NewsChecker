
import pytest
from types import SimpleNamespace

from app.api.routes.analysis import aggregate_claim_verdicts


def make_claims(*verdicts):
    return [
        SimpleNamespace(verdict=verdict)
        for verdict in verdicts
    ]


@pytest.mark.parametrize(
    "verdicts, expected",
    [
        (["supported", "supported"], "claims_supported"),
        (["contradicted", "contradicted"], "disputed"),
        (["supported", "contradicted"], "mixed"),
        (["supported", "mixed"], "mixed"),
        (["mixed", "insufficient_evidence"], "mixed"),
        (["supported", "insufficient_evidence"], "unverified"),
        (["insufficient_evidence", "insufficient_evidence"], "unverified"),
        ([], "unverified"),
    ]
)
def test_aggregate_claim_verdicts(verdicts, expected):

    claims = make_claims(*verdicts)

    status, summary = aggregate_claim_verdicts(claims)

    assert status == expected
    assert isinstance(summary, str)
    assert len(summary) > 0


def test_summary_contains_correct_counts():

    claims = make_claims(
        "supported",
        "supported",
        "contradicted",
        "mixed",
        "insufficient_evidence"
    )

    status, summary = aggregate_claim_verdicts(claims)

    assert status == "mixed"
    assert "Evaluated 5 claims" in summary
    assert "2 supported" in summary
    assert "1 contradicted" in summary
    assert "1 mixed" in summary
    assert "1 with insufficient evidence" in summary


def test_empty_claims_summary():

    status, summary = aggregate_claim_verdicts([])

    assert status == "unverified"
    assert "No claims passed" in summary

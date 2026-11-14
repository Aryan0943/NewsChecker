
from app.services.claim_models import Claim


def test_valid_claim():
    claim = Claim(
        claim_id="C1",
        source_sentence="Police said dozens of protesters were arrested.",
        claim_text="Police said dozens of protesters were arrested.",
        claim_type="reported_statement",
        entities=["Police", "Protesters"],
        location="Dhaka, Bangladesh",
        numbers=["dozens"],
        centrality="high",
        checkable=True,
    )

    assert claim.claim_id == "C1"
    assert claim.claim_type == "reported_statement"
    assert claim.checkable is True


def test_default_values():
    claim = Claim(
        claim_id="C2",
        source_sentence="The factory closed.",
        claim_text="The factory closed.",
        claim_type="event",
    )

    assert claim.entities == []
    assert claim.centrality == "medium"
    assert claim.checkable is True

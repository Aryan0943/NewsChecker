
from typing import Literal

from pydantic import BaseModel, Field


class Claim(BaseModel):
    claim_id: str

    # Original sentence copied from the article
    source_sentence: str

    # Standalone version used for evidence retrieval
    claim_text: str

    claim_type: Literal[
        "event",
        "reported_statement",
        "statistic",
        "historical",
        "scientific",
        "political",
        "other",
    ]

    entities: list[str] = Field(default_factory=list)

    location: str | None = None

    time_reference: str | None = None

    numbers: list[str] = Field(default_factory=list)

    centrality: Literal[
        "high",
        "medium",
        "low",
    ] = "medium"

    checkable: bool = True

    # Whether the standalone claim is supported by article context
    grounding_status: Literal[
        "pending",
        "grounded",
        "needs_review",
        "rejected",
    ] = "pending"

    # Explanation of any grounding concerns
    validation_notes: str | None = None

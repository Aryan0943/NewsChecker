from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ArticleRequest(BaseModel):
    content: str = Field(
        min_length=1,
        max_length=20000,
        description="URL of the article to analyze",
    )

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Article URL cannot be empty.")

        if not value.startswith(("http://", "https://")):
            raise ValueError("Please provide a valid HTTP or HTTPS article URL.")

        return value


class BiasResult(BaseModel):
    category: str
    status: Literal["pending", "analyzed", "error"] = "pending"
    score: float | None = None
    explanation: str = (
        "A real bias analysis model has not been connected yet."
    )


class EvidenceSource(BaseModel):
    title: str | None = None
    domain: str | None = None
    url: str
    excerpt: str


class ClaimFactCheck(BaseModel):
    claim: str
    verdict: Literal[
        "supported",
        "contradicted",
        "mixed",
        "insufficient_evidence",
    ]
    confidence: Literal["low", "medium", "high"]
    explanation: str
    supporting_sources: list[EvidenceSource] = Field(default_factory=list)
    contradicting_sources: list[EvidenceSource] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class FactCheckResult(BaseModel):
    status: Literal[
        "pending",
        "verified",
        "disputed",
        "unverified",
        "claims_supported"
    ] = "pending"

    summary: str = (
        "Automated fact verification has not been completed."
    )

    # Retained for compatibility with your existing frontend.
    sources: list[str] = Field(default_factory=list)

    # New detailed claim-by-claim results.
    claims: list[ClaimFactCheck] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    mode: Literal["url"] = "url"
    article_title: str | None = None
    article_text: str | None = None

    biases: list[BiasResult] = Field(default_factory=list)

    fact_check: FactCheckResult = Field(
        default_factory=FactCheckResult
    )

    message: str

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ArticleRequest(BaseModel):
    mode: Literal["text", "url", "topic"]
    content: str = Field(
        min_length=1,
        max_length=20000,
        description="Article text, article URL, or news topic",
    )

    @model_validator(mode="after")
    def validate_content(self):
        if not self.content.strip():
            raise ValueError("Content cannot be empty or whitespace only")
        return self


class BiasResult(BaseModel):
    category: str
    status: Literal["pending", "analyzed", "error"] = "pending"
    score: float | None = None
    explanation: str = (
        "A real analysis model has not been connected yet."
    )


class FactCheckResult(BaseModel):
    status: Literal["pending", "verified", "disputed", "unverified"] = "pending"
    summary: str = (
        "Automated fact verification has not been implemented yet."
    )
    sources: list[str] = Field(default_factory=list)


class NewsItem(BaseModel):
    title: str
    url: str
    source: str | None = None
    published_at: str | None = None
    description: str | None = None


class AnalysisResponse(BaseModel):
    mode: Literal["text", "url", "topic"]
    article_title: str | None = None
    article_text: str | None = None
    biases: list[BiasResult] = Field(default_factory=list)
    fact_check: FactCheckResult = Field(
        default_factory=FactCheckResult
    )
    related_news: list[NewsItem] = Field(default_factory=list)
    message: str

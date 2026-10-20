import requests
from fastapi import FastAPI, HTTPException

from app.schemas import ArticleRequest, AnalysisResponse
from app.services.article_fetcher import extract_article_text

app = FastAPI(
    title="NewsChecker API",
    description="Backend for the News Bias and Fake News Detection Platform",
    version="0.1.0",
)


@app.get("/")
def home():
    return {
        "message": "NewsChecker API is running!",
        "status": "success",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/analyze", response_model=AnalysisResponse)
def analyze_article(request: ArticleRequest):
    content = request.content.strip()
    article_title = None

    if request.mode == "url":
        try:
            article = extract_article_text(content)
            content = article["text"]
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

    elif request.mode == "topic":
        raise HTTPException(
            status_code=501,
            detail="Topic search will be implemented in a later step.",
        )

    return AnalysisResponse(
        mode=request.mode,
        article_title=article_title,
        article_text=content,
        biases=[
            {"category": "political", "status": "pending"},
            {"category": "gender", "status": "pending"},
            {"category": "communal/caste", "status": "pending"},
            {"category": "cultural", "status": "pending"},
        ],
        fact_check={
            "status": "pending",
            "summary": (
                "Automated fact verification has not been implemented yet."
            ),
            "sources": [],
        },
        related_news=[],
        message=(
            "Article text received successfully. "
            "Real bias analysis and fact-checking are not connected yet."
        ),
    )

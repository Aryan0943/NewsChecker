
import requests

from fastapi import APIRouter, HTTPException

from app.schemas import ArticleRequest, AnalysisResponse
from app.services.article_fetcher import extract_article_text
from app.services.text_preprocessor import preprocess_article
from app.services.news_search import search_news


router = APIRouter()


@router.post("/analyze", response_model=AnalysisResponse)
def analyze_article(request: ArticleRequest):
    content = request.content.strip()
    article_title = None
    related_news = []

    # Fetch and extract article text when a URL is submitted.
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

    # Search for related articles when a topic is submitted.
    elif request.mode == "topic":
        try:
            related_news = search_news(content)

        except RuntimeError as exc:
            raise HTTPException(
                status_code=502,
                detail="News search is not configured or failed.",
            ) from exc

        except requests.RequestException as exc:
            raise HTTPException(
                status_code=502,
                detail="The news service could not be reached.",
            ) from exc

        content = None

    # Clean the text when an article is submitted.
    if request.mode in ("text", "url"):
        content = preprocess_article(content)

    if request.mode == "topic":
        message = (
            f"Found {len(related_news)} articles for the topic "
            f"'{request.content.strip()}'. "
            "Bias analysis and fact-checking are not connected yet."
        )
    else:
        message = (
            "Article text received successfully. "
            "Real bias analysis and fact-checking are not connected yet."
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
        related_news=related_news,
        message=message,
    )

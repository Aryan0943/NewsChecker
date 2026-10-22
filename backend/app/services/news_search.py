
import os
import re
import requests
from dotenv import load_dotenv

from app.schemas import NewsItem


# Load configuration from backend/.env
load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
NEWS_API_URL = "https://newsapi.org/v2/everything"


def search_news(topic: str, page_size: int = 10) -> list[NewsItem]:
    """Search NewsAPI for articles matching a topic."""

    if not NEWS_API_KEY:
        raise RuntimeError(
            "NEWS_API_KEY is missing. Add it to backend/.env."
        )

    response = requests.get(
        NEWS_API_URL,
        params={
            "q": topic,
            "language": "en",
            "sortBy": "relevancy",
            "pageSize": page_size,
            "apiKey": NEWS_API_KEY,
        },
        timeout=15,
    )

    response.raise_for_status()
    data = response.json()

    if data.get("status") != "ok":
        raise RuntimeError("NewsAPI could not complete the search.")

    results = []

    for article in data.get("articles", []):
        title = article.get("title")
        url = article.get("url")

        if not title or not url:
            continue

        results.append(
            NewsItem(
                title=title,
                url=url,
                source=(
                    article.get("source", {}).get("name")
                ),
                published_at=article.get("publishedAt"),
            )
        )

    return results

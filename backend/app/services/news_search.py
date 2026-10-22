

import re
import requests
from app.core.config import NEWS_API_KEY, NEWS_API_URL

from app.schemas import NewsItem




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

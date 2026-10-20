
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


def extract_article_text(url: str) -> dict:
    """Download an article page and extract its readable text."""

    parsed_url = urlparse(url)

    if parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
        raise ValueError("Please provide a valid HTTP or HTTPS URL.")

    response = requests.get(
        url,
        timeout=15,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; NewsChecker/0.1)"
            )
        },
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove elements that usually do not contain article content.
    for element in soup(
        ["script", "style", "nav", "footer", "header", "aside"]
    ):
        element.decompose()

    # Prefer the main article content when available.
    article = soup.find("article") or soup.find("main") or soup.body

    if article is None:
        raise ValueError("Could not find readable content on this page.")

    title = soup.title.get_text(" ", strip=True) if soup.title else None
    text = article.get_text(" ", strip=True)

    if not text:
        raise ValueError("No readable article text was found.")

    return {
        "title": title,
        "text": text[:20000],
        "url": url,
    }

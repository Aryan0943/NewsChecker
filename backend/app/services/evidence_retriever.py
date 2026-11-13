
import os
import re
from urllib.parse import urlparse

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()


# Words that do not help identify the actual subject of a claim.
STOPWORDS = {
    "the", "is", "are", "was", "were", "has", "have", "had",
    "a", "an", "and", "or", "but", "to", "of", "in", "on",
    "at", "by", "for", "from", "with", "after", "before",
    "during", "that", "this", "these", "those", "their",
    "they", "them", "he", "she", "it", "who", "which",
    "what", "when", "where", "while", "also", "said",
    "according", "reported", "reportedly", "could", "would",
    "should", "been", "being", "into", "than", "more",
    "over", "under", "about", "around"
}


EXCLUDED_DOMAINS = {
    "facebook.com",
    "youtube.com",
    "youtu.be",
    "instagram.com",
    "tiktok.com",
    "x.com",
    "twitter.com",
}


def get_tavily_client():
    api_key = os.getenv("TAVILY_API_KEY")

    if not api_key:
        raise RuntimeError("TAVILY_API_KEY is missing.")

    return TavilyClient(api_key=api_key)


def clean_evidence_text(text: str) -> str:
    if not text:
        return ""

    text = re.sub(
        r"\bAdvertisement\b",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def extract_keywords(text: str) -> set[str]:
    """Extract meaningful words for basic relevance checking."""

    words = re.findall(r"[a-zA-Z0-9]+", text.lower())

    return {
        word
        for word in words
        if len(word) > 2 and word not in STOPWORDS
    }


def calculate_relevance(claim: str, evidence_text: str) -> float:
    """
    Calculate basic keyword overlap.

    This is a retrieval filter, NOT a truth or confidence score.
    """

    claim_keywords = extract_keywords(claim)
    evidence_keywords = extract_keywords(evidence_text)

    if not claim_keywords or not evidence_keywords:
        return 0.0

    overlap = claim_keywords.intersection(evidence_keywords)

    return len(overlap) / len(claim_keywords)


def search_evidence(
    claim: str,
    max_results: int = 5,
    context: str = ""
) -> list[dict]:
    """Retrieve evidence and filter obviously unrelated results."""

    if not claim or not claim.strip():
        return []

    # Add article context to help distinguish similar events.
    search_query = f"{claim} {context}".strip()

    client = get_tavily_client()

    response = client.search(
        query=search_query,
        search_depth="advanced",
        max_results=max_results * 2,
        include_answer=False,
        include_raw_content=False,
    )

    evidence = []
    seen_urls = set()

    for result in response.get("results", []):

        url = result.get("url", "")

        if not url:
            continue

        domain = urlparse(url).netloc.lower()

        if any(
            domain == blocked or domain.endswith("." + blocked)
            for blocked in EXCLUDED_DOMAINS
        ):
            continue

        if url in seen_urls:
            continue

        title = result.get("title") or ""

        content = clean_evidence_text(
            result.get("content") or ""
        )

        if not content:
            continue

        # Check relevance against the claim and its article context.
        comparison_text = f"{title} {content}"

        relevance = calculate_relevance(
            search_query,
            comparison_text
        )

        # Reject results with very little keyword overlap.
        if relevance < 0.15:
            continue

        seen_urls.add(url)

        evidence.append({
            "title": title,
            "url": url,
            "domain": domain,
            "content": content,
            "published_date": result.get("published_date"),
            "relevance_score": result.get("score"),
            "keyword_relevance": round(relevance, 3),
        })

        if len(evidence) >= max_results:
            break

    return evidence

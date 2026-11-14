
from urllib.parse import quote_plus
import re





def extract_claims(article_text: str, max_claims: int = 5) -> list[str]:
    """Extract clean candidate factual statements from article text."""

    if not article_text or not article_text.strip():
        return []

    # Split article into paragraphs.
    paragraphs = re.split(r"\n+", article_text.strip())

    claims = []

    ignored_phrases = (
        "watch:",
        "read more",
        "listen:",
        "photo credit",
        "image:",
        "published:",
        "updated:",
        "subscribe",
        "advertisement",
        "also read",
    )

    promotional_phrases = (
        "cements its position",
        "global powerhouse",
        "aspirations of its farmers",
        "next frontier of growth",
        "emerging opportunities",
        "landmark",
        "pivotal moment",
        "driving force",
    )

    for paragraph in paragraphs:

        paragraph = paragraph.strip()

        if not paragraph:
            continue

        # Split sentences while preserving their original text.
        sentences = re.split(
            r"(?<=[.!?])\s+(?=[A-Z0-9\"'])",
            paragraph,
        )

        for sentence in sentences:

            sentence = sentence.strip()

            if len(sentence) < 45 or len(sentence) > 400:
                continue

            lowered = sentence.lower()

            if sentence.endswith("?"):
                continue

            if lowered.startswith(ignored_phrases):
                continue

            if any(
                phrase in lowered
                for phrase in promotional_phrases
            ):
                continue

            if "|" in sentence:
                continue

            # Avoid duplicate sentences.
            if sentence not in claims:
                claims.append(sentence)

            if len(claims) >= max_claims:
                return claims

    return claims




def search_claim(claim: str, article_text: str = "") -> list[dict[str, str]]:
    """Generate searches from sources relevant to the article."""

    query = quote_plus(claim)
    article_context = article_text.lower()

    sources = []

    # Prioritize PIB for Indian government-related content.
    india_keywords = [
        "india",
        "indian government",
        "ministry",
        "prime minister of india",
        "government of india",
    ]

    if any(keyword in article_context for keyword in india_keywords):
        sources.append({
            "source": "PIB Fact Check",
            "url": (
                "https://www.google.com/search?q="
                f"site%3Apib.gov.in%2Ffactcheck+{query}"
            ),
        })

    # BOOM can be searched for broader misinformation claims.
    sources.append({
        "source": "BOOM Live",
        "url": (
            "https://www.google.com/search?q="
            f"site%3Aboomlive.in%2Ffact-check+{query}"
        ),
    })

    return sources


def fact_check_article(article_text: str) -> dict:
    """Prepare candidate claims and searches for manual evidence review."""

    claims = extract_claims(article_text)

    results = []

    for claim in claims:
        results.append({
            "claim": claim,
            "status": "awaiting_verification",
            "sources": search_claim(claim, article_text),
        })

    return {
        "status": "pending",
        "message": (
            "Candidate claims and source-specific searches are ready. "
            "Search results must be reviewed before assigning a verdict."
        ),
        "claims": results,
    }

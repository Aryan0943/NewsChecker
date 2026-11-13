
import re
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse


PUBLICATION_ALIASES = {
    "thedailystar.net": ["the daily star", "daily star"],
    "business-standard.com": ["business standard"],
    "asianews.network": ["asia news network"],
    "seekingalpha.com": ["seeking alpha"],
    "reuters.com": ["reuters"],
    "apnews.com": ["associated press", "ap"],
    "thehindu.com": ["the hindu"],
    "ndtv.com": ["ndtv"],
    "livemint.com": ["livemint", "live mint"],
    "theprint.in": ["the print"],
    "economictimes.indiatimes.com": ["economic times", "et"],
    "pmindia.gov.in": ["prime minister of india"],
    "pib.gov.in": ["press information bureau", "pib"],
}


TRACKING_PARAMETERS = {
    "fbclid",
    "gclid",
    "dclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
}


ATTRIBUTION_PHRASES = [
    "reported by",
    "according to",
    "citing",
    "as reported by",
    "as per",
    "based on a report by",
    "according to a report by",
    "news agency",
    "agency report",
    "reuters reported",
    "associated press reported",
]


def get_domain(url: str) -> str:
    if not url:
        return ""

    try:
        domain = urlparse(url).netloc.lower()
        return domain.removeprefix("www.")
    except Exception:
        return ""


def normalize_url(url: str) -> str:
    """
    Normalize URLs for duplicate detection.

    Removes fragments and common tracking parameters.
    Preserves meaningful query parameters.
    """

    if not url:
        return ""

    try:
        parsed = urlparse(url.strip())

        domain = parsed.netloc.lower().removeprefix("www.")
        path = parsed.path.rstrip("/")

        query_parameters = [
            (key, value)
            for key, value in parse_qsl(
                parsed.query,
                keep_blank_values=True
            )
            if not (
                key.lower().startswith("utm_")
                or key.lower() in TRACKING_PARAMETERS
            )
        ]

        query_parameters.sort()

        query = urlencode(query_parameters)

        return urlunparse((
            parsed.scheme.lower() or "https",
            domain,
            path,
            "",
            query,
            ""
        ))

    except Exception:
        return url.strip()


def normalize_content(text: str) -> str:
    if not text:
        return ""

    text = text.lower()

    text = re.sub(
        r"https?://\S+",
        "",
        text
    )

    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def get_word_shingles(
    text: str,
    size: int = 4
) -> set:

    words = normalize_content(text).split()

    if len(words) < size:
        return set()

    return {
        " ".join(words[i:i + size])
        for i in range(len(words) - size + 1)
    }


def calculate_similarity(
    text1: str,
    text2: str
) -> float:
    """
    Calculate Jaccard similarity between article shingles.

    Unlike containment similarity, this penalizes large
    differences in article length.
    """

    shingles1 = get_word_shingles(text1)
    shingles2 = get_word_shingles(text2)

    if not shingles1 or not shingles2:
        return 0.0

    intersection = len(
        shingles1.intersection(shingles2)
    )

    union = len(
        shingles1.union(shingles2)
    )

    if union == 0:
        return 0.0

    return intersection / union


def get_publication_aliases(source: dict) -> set:
    aliases = set()

    domain = get_domain(
        source.get("url", "")
    )

    aliases.update(
        PUBLICATION_ALIASES.get(domain, [])
    )

    title = source.get("title") or ""

    parts = re.split(
        r"\s+[|–—-]\s+",
        title
    )

    if len(parts) > 1:
        publisher = parts[-1].strip().lower()

        if len(publisher) >= 4:
            aliases.add(publisher)

    return aliases


def detect_attribution(
    evidence: list[dict]
) -> list[dict]:

    relationships = []

    for source in evidence:

        content = normalize_content(
            source.get("content", "")
        )

        for other_source in evidence:

            if source is other_source:
                continue

            aliases = get_publication_aliases(
                other_source
            )

            for alias in aliases:

                normalized_alias = normalize_content(
                    alias
                )

                for phrase in ATTRIBUTION_PHRASES:

                    normalized_phrase = normalize_content(
                        phrase
                    )

                    search_phrase = (
                        normalized_phrase
                        + " "
                        + normalized_alias
                    )

                    if search_phrase in content:

                        relationships.append({
                            "from_source": source.get("url"),
                            "to_source": other_source.get("url"),
                            "relationship": "possible_attribution",
                            "matched_text": search_phrase
                        })

                        break

    return relationships



def exclude_original_article(
    evidence: list[dict],
    original_article_url: str | None
) -> tuple[list[dict], list[dict]]:

    if not original_article_url:
        return evidence, []

    original_parsed = urlparse(original_article_url.strip())
    original_domain = original_parsed.netloc.lower().removeprefix("www.")
    original_path = original_parsed.path.rstrip("/")

    filtered = []
    excluded = []

    for source in evidence:
        source_url = source.get("url", "")

        if not source_url:
            filtered.append(source)
            continue

        source_parsed = urlparse(source_url.strip())
        source_domain = source_parsed.netloc.lower().removeprefix("www.")
        source_path = source_parsed.path.rstrip("/")

        same_domain = source_domain == original_domain

        # Exact path match, including AMP variants.
        same_path = (
            source_path == original_path
            or source_path == original_path + "/amp"
            or source_path == original_path + "/amp/"
        )

        if same_domain and same_path:
            excluded.append({
                "url": source_url,
                "reason": "original_article_excluded"
            })
        else:
            filtered.append(source)

    return filtered, excluded



def analyze_sources(
    evidence: list[dict],
    similarity_threshold: float = 0.30,
    original_article_url: str | None = None
) -> dict:

    if not evidence:
        return {
            "sources": [],
            "duplicate_groups": [],
            "similarity_groups": [],
            "attribution_relationships": [],
            "excluded_sources": [],
            "source_count": 0,
            "unique_source_count": 0,
            "independent_group_count": 0,
            "independence_assessment": "insufficient_sources"
        }

    # STEP 1: Exclude the original article.

    filtered_sources, excluded_sources = (
        exclude_original_article(
            evidence,
            original_article_url
        )
    )

    # STEP 2: Remove duplicate URLs.

    unique_sources = []
    seen_urls = set()
    duplicate_groups = []

    for source in filtered_sources:

        normalized_url = normalize_url(
            source.get("url", "")
        )

        if not normalized_url:
            continue

        if normalized_url in seen_urls:

            duplicate_groups.append({
                "url": source.get("url"),
                "reason": "duplicate_url"
            })

            continue

        seen_urls.add(normalized_url)
        unique_sources.append(source)

    # STEP 3: Detect similar content.

    similarity_groups = []

    for i in range(len(unique_sources)):

        for j in range(i + 1, len(unique_sources)):

            source1 = unique_sources[i]
            source2 = unique_sources[j]

            similarity = calculate_similarity(
                source1.get("content", ""),
                source2.get("content", "")
            )

            if similarity >= similarity_threshold:

                similarity_groups.append({
                    "source_1": source1.get("url"),
                    "source_2": source2.get("url"),
                    "similarity": round(similarity, 3),
                    "possible_shared_reporting": True
                })

    # STEP 4: Detect explicit attribution.

    attribution_relationships = detect_attribution(
        unique_sources
    )

    # STEP 5: Build conservative source groups.
    # Sources with similar content or explicit attribution
    # are treated as potentially dependent.

    parent = list(range(len(unique_sources)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]

        return x

    def union(a, b):
        root_a = find(a)
        root_b = find(b)

        if root_a != root_b:
            parent[root_b] = root_a

    url_to_index = {
        normalize_url(source.get("url", "")): index
        for index, source in enumerate(unique_sources)
    }

    for relationship in similarity_groups:

        index1 = url_to_index.get(
            normalize_url(relationship["source_1"])
        )

        index2 = url_to_index.get(
            normalize_url(relationship["source_2"])
        )

        if index1 is not None and index2 is not None:
            union(index1, index2)

    for relationship in attribution_relationships:

        index1 = url_to_index.get(
            normalize_url(relationship["from_source"])
        )

        index2 = url_to_index.get(
            normalize_url(relationship["to_source"])
        )

        if index1 is not None and index2 is not None:
            union(index1, index2)

    groups = {}

    for index, source in enumerate(unique_sources):

        root = find(index)

        groups.setdefault(root, []).append(
            source.get("url")
        )

    independent_group_count = len(groups)

    # STEP 6: Produce an assessment.

    if len(unique_sources) == 0:
        assessment = "no_usable_sources"

    elif independent_group_count == 1:
        assessment = "limited_independent_corroboration"

    elif independent_group_count < 3:
        assessment = "some_independent_corroboration"

    else:
        assessment = "multiple_potentially_independent_sources"

    return {
        "sources": unique_sources,
        "duplicate_groups": duplicate_groups,
        "similarity_groups": similarity_groups,
        "attribution_relationships": attribution_relationships,
        "excluded_sources": excluded_sources,
        "source_count": len(evidence),
        "unique_source_count": len(unique_sources),
        "independent_group_count": independent_group_count,
        "independence_groups": list(groups.values()),
        "independence_assessment": assessment
    }

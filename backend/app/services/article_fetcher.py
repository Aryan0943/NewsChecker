
import html
import ipaddress
import json
import re
import socket

from email.message import Message
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURATION
# ============================================================

MAX_PAGE_SIZE = 5_000_000       # 5 MB HTML response
MAX_ARTICLE_CHARS = 50_000      # Maximum returned article text
MAX_REDIRECTS = 5
MIN_ARTICLE_LENGTH = 500

REQUEST_TIMEOUT = (5, 20)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0 Safari/537.36"
)


# ============================================================
# 1. URL VALIDATION
# ============================================================

def validate_public_url(url: str) -> None:
    """
    Validate HTTP/HTTPS URLs and reject non-public IP addresses.

    Note:
    DNS validation followed by a normal requests connection
    does not completely prevent DNS rebinding attacks.
    Production deployment needs connection-level protection.
    """

    parsed_url = urlparse(url)

    if parsed_url.scheme not in {"http", "https"}:
        raise ValueError("Only HTTP and HTTPS URLs are allowed.")

    if not parsed_url.hostname:
        raise ValueError("Please provide a valid URL.")

    if parsed_url.username or parsed_url.password:
        raise ValueError(
            "URLs containing login credentials are not allowed."
        )

    hostname = parsed_url.hostname

    try:
        ip_addresses = {
            ipaddress.ip_address(hostname)
        }

    except ValueError:

        try:
            resolved_addresses = socket.getaddrinfo(
                hostname,
                None,
                type=socket.SOCK_STREAM,
            )

            ip_addresses = {
                ipaddress.ip_address(result[4][0])
                for result in resolved_addresses
            }

        except (socket.gaierror, ValueError):
            raise ValueError(
                "The URL hostname could not be resolved."
            )

    if not ip_addresses:
        raise ValueError(
            "The hostname has no valid IP addresses."
        )

    for ip in ip_addresses:

        if not ip.is_global:
            raise ValueError(
                "URLs pointing to private or restricted "
                "addresses are not allowed."
            )


def get_safe_redirect_url(
    base_url: str,
    location: str,
) -> str:
    """Resolve and validate a redirect destination."""

    redirect_url = urljoin(base_url, location)

    validate_public_url(redirect_url)

    return redirect_url


# ============================================================
# 2. HTML ENCODING DETECTION
# ============================================================

def decode_html_response(
    response: requests.Response,
    content: bytes,
) -> str:
    """
    Decode HTML without blindly trusting requests' default
    ISO-8859-1 encoding.

    Priority:
    1. BOM
    2. HTTP Content-Type charset
    3. HTML meta charset
    4. Requests apparent encoding
    5. UTF-8 fallback
    """

    # --------------------------------------------------------
    # 1. BOM detection
    # --------------------------------------------------------

    if content.startswith(b"\xef\xbb\xbf"):
        return content.decode(
            "utf-8-sig",
            errors="replace",
        )

    if content.startswith(b"\xff\xfe"):
        return content.decode(
            "utf-16",
            errors="replace",
        )

    if content.startswith(b"\xfe\xff"):
        return content.decode(
            "utf-16-be",
            errors="replace",
        )

    # --------------------------------------------------------
    # 2. HTTP charset
    # --------------------------------------------------------

    message = Message()

    message["content-type"] = response.headers.get(
        "Content-Type",
        "",
    )

    charset = message.get_content_charset()

    if charset:

        try:
            return content.decode(
                charset,
                errors="replace",
            )

        except (LookupError, UnicodeDecodeError):
            pass

    # --------------------------------------------------------
    # 3. HTML meta charset
    # --------------------------------------------------------

    meta_charset = re.search(
        rb'<meta[^>]+charset\s*=\s*["\']?\s*'
        rb'([a-zA-Z0-9._-]+)',
        content[:8192],
        re.IGNORECASE,
    )

    if meta_charset:

        detected_charset = meta_charset.group(
            1
        ).decode(
            "ascii",
            errors="ignore",
        )

        try:
            return content.decode(
                detected_charset,
                errors="replace",
            )

        except (LookupError, UnicodeDecodeError):
            pass

    # --------------------------------------------------------
    # 4. Requests apparent encoding
    # --------------------------------------------------------

    try:
        detected_encoding = response.apparent_encoding

        if detected_encoding:
            return content.decode(
                detected_encoding,
                errors="replace",
            )

    except (LookupError, UnicodeDecodeError):
        pass

    # --------------------------------------------------------
    # 5. Final fallback
    # --------------------------------------------------------

    return content.decode(
        "utf-8",
        errors="replace",
    )


# ============================================================
# 3. TEXT CLEANING
# ============================================================

def clean_text(text: str) -> str:
    """
    Decode HTML entities and normalize whitespace.

    Preserve paragraph boundaries and sentence punctuation.
    """

    if not text:
        return ""

    text = html.unescape(text)

    text = (
        text.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\xa0", " ")
        .replace("\u200b", "")
    )

    paragraphs = []

    for paragraph in text.split("\n"):

        paragraph = re.sub(
            r"[ \t]+",
            " ",
            paragraph,
        ).strip()

        if paragraph:
            paragraphs.append(paragraph)

    return "\n\n".join(paragraphs)


def normalize_paragraph(text: str) -> str:
    """Normalize paragraph text for duplicate detection."""

    return re.sub(
        r"\s+",
        " ",
        text.lower(),
    ).strip()


def remove_duplicate_paragraphs(text: str) -> str:
    """Remove exact duplicate paragraphs while preserving order."""

    paragraphs = text.split("\n\n")

    seen = set()
    unique_paragraphs = []

    for paragraph in paragraphs:

        normalized = normalize_paragraph(paragraph)

        if not normalized:
            continue

        if normalized in seen:
            continue

        seen.add(normalized)

        unique_paragraphs.append(
            paragraph.strip()
        )

    return "\n\n".join(unique_paragraphs)


# ============================================================
# 4. JSON-LD EXTRACTION
# ============================================================

ARTICLE_TYPES = {
    "Article",
    "NewsArticle",
    "ReportageNewsArticle",
    "AnalysisNewsArticle",
    "BlogPosting",
}


def extract_json_ld(soup: BeautifulSoup) -> list:
    """Extract JSON-LD structured data."""

    json_ld_data = []

    for script in soup.find_all(
        "script",
        type="application/ld+json",
    ):

        try:
            raw_data = script.string or script.get_text()

            data = json.loads(raw_data)

            json_ld_data.append(data)

        except (json.JSONDecodeError, TypeError):
            continue

    return json_ld_data


def find_article_objects(data) -> list[dict]:
    """Recursively locate article objects in JSON-LD."""

    found_articles = []

    if isinstance(data, dict):

        item_type = data.get("@type")

        if isinstance(item_type, str):
            types = {item_type}

        elif isinstance(item_type, list):
            types = set(item_type)

        else:
            types = set()

        if types.intersection(ARTICLE_TYPES):
            found_articles.append(data)

        for value in data.values():

            found_articles.extend(
                find_article_objects(value)
            )

    elif isinstance(data, list):

        for item in data:

            found_articles.extend(
                find_article_objects(item)
            )

    return found_articles


def extract_json_article_body(
    articles: list[dict],
) -> str:
    """Extract the longest structured articleBody."""

    candidates = []

    for article in articles:

        body = article.get("articleBody")

        if isinstance(body, str) and body.strip():

            candidates.append(
                clean_text(body)
            )

    if not candidates:
        return ""

    return max(
        candidates,
        key=len,
    )


# ============================================================
# 5. ARTICLE METADATA
# ============================================================

def extract_title(
    soup: BeautifulSoup,
    articles: list[dict],
):
    """Extract the article title."""

    for article in articles:

        headline = article.get("headline")

        if isinstance(headline, str) and headline.strip():

            return html.unescape(
                headline.strip()
            )

    og_title = soup.find(
        "meta",
        property="og:title",
    )

    if og_title and og_title.get("content"):

        return html.unescape(
            og_title["content"].strip()
        )

    h1 = soup.find("h1")

    if h1:

        return html.unescape(
            h1.get_text(" ", strip=True)
        )

    if soup.title:

        return html.unescape(
            soup.title.get_text(" ", strip=True)
        )

    return None


def extract_date(
    soup: BeautifulSoup,
    articles: list[dict],
):
    """Extract article publication date."""

    # JSON-LD
    for article in articles:

        date = (
            article.get("datePublished")
            or article.get("dateCreated")
        )

        if date:
            return str(date)

    # Metadata
    date_selectors = [
        ("meta", {"property": "article:published_time"}),
        ("meta", {"name": "date"}),
        ("meta", {"name": "publishdate"}),
        ("meta", {"name": "pubdate"}),
        ("meta", {"name": "DC.date.issued"}),
        ("meta", {"itemprop": "datePublished"}),
    ]

    for tag, attributes in date_selectors:

        element = soup.find(
            tag,
            attrs=attributes,
        )

        if element:

            value = (
                element.get("content")
                or element.get("datetime")
            )

            if value:
                return value.strip()

    time_element = soup.find(
        "time",
        attrs={"datetime": True},
    )

    if time_element:
        return time_element["datetime"].strip()

    return None


# ============================================================
# 6. PAGE CLUTTER REMOVAL
# ============================================================

REMOVE_TAGS = [
    "script",
    "style",
    "nav",
    "footer",
    "aside",
    "form",
    "button",
    "input",
    "svg",
    "noscript",
    "iframe",
]


CLUTTER_TERMS = {
    "newsletter",
    "advert",
    "advertisement",
    "social-share",
    "breadcrumb",
    "related",
    "recommended",
    "more-stories",
    "trending",
    "most-read",
    "comments",
    "cookie",
    "subscription",
    "subscribe",
    "navigation",
    "read-more",
}


NEGATIVE_PREFIXES = {
    "no",
    "not",
    "without",
    "non",
}


def is_clutter_element(element) -> bool:
    """
    Identify likely clutter modules.

    Do not remove body/html/main/article or containers
    that contain the actual article.
    """

    if element.name in {
        "html",
        "body",
        "main",
        "article",
    }:
        return False

    # Preserve structural ancestors of article containers.
    if element.find(["article", "main"]):
        return False

    raw_classes = element.get("class", [])

    raw_id = element.get("id", "")

    values = list(raw_classes) + [raw_id]

    for value in values:

        tokens = re.split(
            r"[-_\s]+",
            str(value).lower(),
        )

        for index, token in enumerate(tokens):

            # Avoid false positives:
            # no-paywall, no-comments, without-advertising.
            if index > 0 and tokens[index - 1] in NEGATIVE_PREFIXES:
                continue

            if token in CLUTTER_TERMS:
                return True

    return False


def remove_page_clutter(
    soup: BeautifulSoup,
) -> BeautifulSoup:
    """Remove page clutter without destroying article wrappers."""

    # Remove unambiguously non-content tags.
    for element in list(soup.find_all(REMOVE_TAGS)):

        if element.parent is not None:
            element.decompose()

    # Process inner elements before their ancestors.
    elements = list(soup.find_all(True))

    for element in reversed(elements):

        if element.parent is None:
            continue

        if not is_clutter_element(element):
            continue

        # Preserve large content containers.
        # A large comments/recommendations container needs
        # more specific publisher-specific filtering later.
        text = element.get_text(
            " ",
            strip=True,
        )

        article_paragraphs = element.find_all("p")

        if (
            len(article_paragraphs) >= 2
            or len(text) >= 500
        ):
            continue

        element.decompose()

    return soup


# ============================================================
# 7. PARAGRAPH EXTRACTION
# ============================================================

def get_paragraphs(element) -> list[str]:
    """Extract meaningful paragraphs from a container."""

    paragraphs = []

    for paragraph in element.find_all("p"):

        # Ignore paragraphs nested in obvious clutter.
        if paragraph.find_parent(
            ["nav", "aside", "footer", "form"]
        ):
            continue

        text = clean_text(
            paragraph.get_text(" ", strip=True)
        )

        # Short factual statements must be preserved.
        # Example: "No injuries were reported."
        if len(text) >= 15:
            paragraphs.append(text)

    return paragraphs


# ============================================================
# 8. CANDIDATE SCORING
# ============================================================

def score_article_candidate(
    element,
    priority: int,
) -> float:
    """
    Score candidate containers.

    Factors:
    - Article-specific selector priority.
    - Paragraph count.
    - Content length.
    - Link-text density.

    A larger container does not automatically win.
    """

    paragraphs = get_paragraphs(element)

    if not paragraphs:
        return 0

    text = "\n\n".join(paragraphs)

    if len(text) < 300:
        return 0

    text_length = len(text)

    link_text_length = sum(
        len(
            link.get_text(
                " ",
                strip=True,
            )
        )
        for link in element.find_all("a")
    )

    link_ratio = (
        link_text_length / max(text_length, 1)
    )

    paragraph_count = len(paragraphs)

    score = (
        priority * 500
        + min(text_length, 15000) * 0.5
        + paragraph_count * 100
        - link_ratio * 3000
    )

    return score


# ============================================================
# 9. SEMANTIC ARTICLE EXTRACTION
# ============================================================

def extract_semantic_article_body(
    soup: BeautifulSoup,
) -> str:
    """Extract from article-specific HTML containers."""

    selectors = [
        (
            {"itemprop": "articleBody"},
            6,
        ),
        (
            {"class": re.compile(r"article[-_]?body", re.I)},
            6,
        ),
        (
            {"class": re.compile(r"story[-_]?body", re.I)},
            6,
        ),
        (
            {"id": re.compile(r"article[-_]?body", re.I)},
            6,
        ),
        (
            {"class": re.compile(r"article[-_]?content", re.I)},
            4,
        ),
        (
            {"class": re.compile(r"story[-_]?content", re.I)},
            4,
        ),
    ]

    candidates = []

    seen = set()

    for attributes, priority in selectors:

        for element in soup.find_all(
            attrs=attributes
        ):

            paragraphs = get_paragraphs(element)

            if not paragraphs:
                continue

            text = remove_duplicate_paragraphs(
                "\n\n".join(paragraphs)
            )

            if len(text) < 300:
                continue

            if text in seen:
                continue

            seen.add(text)

            score = score_article_candidate(
                element,
                priority,
            )

            candidates.append(
                (score, text)
            )

    if not candidates:
        return ""

    return max(
        candidates,
        key=lambda item: item[0],
    )[1]


# ============================================================
# 10. ARTICLE / MAIN PARAGRAPH FALLBACK
# ============================================================

def extract_paragraph_body(
    soup: BeautifulSoup,
) -> str:
    """Extract paragraphs from article/main containers."""

    candidates = []

    seen = set()

    for container in soup.find_all(
        ["article", "main"]
    ):

        paragraphs = get_paragraphs(container)

        if not paragraphs:
            continue

        text = remove_duplicate_paragraphs(
            "\n\n".join(paragraphs)
        )

        if len(text) < 300:
            continue

        if text in seen:
            continue

        seen.add(text)

        score = score_article_candidate(
            container,
            priority=3 if container.name == "article" else 2,
        )

        candidates.append(
            (score, text)
        )

    if not candidates:
        return ""

    return max(
        candidates,
        key=lambda item: item[0],
    )[1]


# ============================================================
# 11. EXTRACTION QUALITY
# ============================================================

def assess_extraction_quality(
    text: str,
) -> dict:
    """Calculate basic extraction quality indicators."""

    paragraphs = [
        paragraph.strip()
        for paragraph in text.split("\n\n")
        if paragraph.strip()
    ]

    word_count = len(text.split())

    if len(text) < 500 or word_count < 80:
        quality = "low"

    elif len(paragraphs) < 3 or word_count < 150:
        quality = "medium"

    else:
        quality = "acceptable"

    return {
        "quality": quality,
        "paragraph_count": len(paragraphs),
        "word_count": word_count,
    }


# ============================================================
# 12. DOWNLOAD PAGE SAFELY
# ============================================================

def download_page(url: str) -> tuple[str, str]:
    """
    Download an HTML page with redirect validation and
    a maximum response size.
    """

    current_url = url

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,*/*;q=0.8"
        ),
    }

    for redirect_count in range(MAX_REDIRECTS + 1):

        validate_public_url(current_url)

        response = requests.get(
            current_url,
            timeout=REQUEST_TIMEOUT,
            headers=headers,
            allow_redirects=False,
            stream=True,
        )

        try:

            if (
                response.is_redirect
                or response.is_permanent_redirect
            ):

                if redirect_count == MAX_REDIRECTS:
                    raise ValueError("Too many redirects.")

                location = response.headers.get(
                    "Location"
                )

                if not location:
                    raise ValueError(
                        "Redirect response has no destination."
                    )

                current_url = get_safe_redirect_url(
                    current_url,
                    location,
                )

                continue

            if response.status_code == 403:
                raise ValueError(
                    "This publisher denied automated access (HTTP 403). "
                    "Try another article URL or use an authorized content source."
                )

            if response.status_code == 401:
                raise ValueError(
                    "This article requires authentication (HTTP 401)."
                )

            if response.status_code == 429:
                raise ValueError(
                    "The publisher is rate-limiting requests (HTTP 429). "
                    "Please wait before trying again."
                )

            response.raise_for_status()

            content_type = response.headers.get(
                "Content-Type",
                "",
            ).lower()

            if "text/html" not in content_type:
                raise ValueError(
                    "The supplied URL did not return an HTML page."
                )

            content_length = response.headers.get(
                "Content-Length"
            )

            if content_length:

                try:
                    if int(content_length) > MAX_PAGE_SIZE:
                        raise ValueError(
                            "Article page exceeds the allowed size."
                        )
                except ValueError as error:

                    if "exceeds" in str(error):
                        raise

            content = bytearray()

            for chunk in response.iter_content(
                chunk_size=8192
            ):

                if not chunk:
                    continue

                content.extend(chunk)

                if len(content) > MAX_PAGE_SIZE:
                    raise ValueError(
                        "Article page exceeds the allowed size."
                    )

            page_html = decode_html_response(
                response,
                bytes(content),
            )

            return current_url, page_html

        finally:
            response.close()

    raise ValueError("Could not retrieve the article.")


# ============================================================
# 13. MAIN ARTICLE FETCHER
# ============================================================

def extract_article_text(url: str) -> dict:
    """
    Fetch and extract the main content of a news article.

    Extraction priority:
    1. Cleaned semantic HTML.
    2. Article/main paragraph extraction.
    3. JSON-LD articleBody fallback.

    Returns article text, metadata and extraction diagnostics.
    """

    validate_public_url(url)

    current_url, page_html = download_page(url)

    # --------------------------------------------------------
    # Parse original page
    # --------------------------------------------------------

    original_soup = BeautifulSoup(
        page_html,
        "html.parser",
    )

    structured_data = extract_json_ld(
        original_soup
    )

    articles = []

    for item in structured_data:

        articles.extend(
            find_article_objects(item)
        )

    title = extract_title(
        original_soup,
        articles,
    )

    published_date = extract_date(
        original_soup,
        articles,
    )

    json_ld_text = extract_json_article_body(
        articles
    )

    # --------------------------------------------------------
    # Prepare cleaned DOM
    # --------------------------------------------------------

    cleaned_soup = BeautifulSoup(
        page_html,
        "html.parser",
    )

    cleaned_soup = remove_page_clutter(
        cleaned_soup
    )

    # --------------------------------------------------------
    # Candidate 1: semantic article HTML
    # --------------------------------------------------------

    semantic_text = extract_semantic_article_body(
        cleaned_soup
    )

    # --------------------------------------------------------
    # Candidate 2: article/main paragraphs
    # --------------------------------------------------------

    paragraph_text = extract_paragraph_body(
        cleaned_soup
    )

    # --------------------------------------------------------
    # Select DOM candidate
    # --------------------------------------------------------

    dom_candidates = []

    if len(semantic_text) >= MIN_ARTICLE_LENGTH:
        dom_candidates.append(
            ("semantic_html", semantic_text)
        )

    if len(paragraph_text) >= MIN_ARTICLE_LENGTH:
        dom_candidates.append(
            ("article_paragraphs", paragraph_text)
        )

    if dom_candidates:

        # Semantic article-specific containers get preference.
        # Paragraph extraction is a fallback, not automatically
        # selected just because its container is larger.
        extraction_method, article_text = max(
            dom_candidates,
            key=lambda item: (
                1 if item[0] == "semantic_html" else 0,
                len(item[1]),
            ),
        )

    elif len(json_ld_text) >= MIN_ARTICLE_LENGTH:

        extraction_method = "json_ld"
        article_text = json_ld_text

    else:

        best_length = max(
            len(semantic_text),
            len(paragraph_text),
            len(json_ld_text),
        )

        raise ValueError(
            "Article extraction appears incomplete. "
            f"Only {best_length} characters were extracted. "
            "The publisher may use JavaScript rendering, "
            "block automated requests, or provide insufficient "
            "article content."
        )

    # --------------------------------------------------------
    # Final cleaning
    # --------------------------------------------------------

    article_text = clean_text(
        article_text
    )

    article_text = remove_duplicate_paragraphs(
        article_text
    )

    if len(article_text) < MIN_ARTICLE_LENGTH:

        raise ValueError(
            "Extracted article text is too short "
            "for reliable analysis."
        )

    # --------------------------------------------------------
    # Quality and truncation information
    # --------------------------------------------------------

    quality = assess_extraction_quality(
        article_text
    )

    original_text_length = len(article_text)

    truncated = (
        original_text_length > MAX_ARTICLE_CHARS
    )

    returned_text = article_text[
        :MAX_ARTICLE_CHARS
    ]

    return {
        "title": title,
        "text": returned_text,
        "url": current_url,
        "published_date": published_date,
        "extraction_method": extraction_method,
        "text_length": original_text_length,
        "returned_text_length": len(returned_text),
        "word_count": quality["word_count"],
        "paragraph_count": quality["paragraph_count"],
        "extraction_quality": quality["quality"],
        "truncated": truncated,
    }

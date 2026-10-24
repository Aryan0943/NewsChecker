
import ipaddress
import socket
from urllib.parse import urlparse,urljoin

import requests
from bs4 import BeautifulSoup


def validate_public_url(url: str) -> None:
    """Reject URLs that point to non-public network addresses."""

    parsed_url = urlparse(url)

    if parsed_url.scheme not in {"http", "https"}:
        raise ValueError("Only HTTP and HTTPS URLs are allowed.")

    if not parsed_url.hostname:
        raise ValueError("Please provide a valid URL with a hostname.")

    if parsed_url.username or parsed_url.password:
        raise ValueError("URLs containing login credentials are not allowed.")

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
            raise ValueError("The URL hostname could not be resolved.")

    if not ip_addresses:
        raise ValueError("The URL hostname has no valid IP addresses.")

    for ip in ip_addresses:
        if not ip.is_global:
            raise ValueError("URLs pointing to private or restricted addresses are not allowed.")


def get_safe_redirect_url(base_url: str, location: str) -> str:
    """Resolve and validate a redirect destination."""
    

    redirect_url = urljoin(base_url, location)
    validate_public_url(redirect_url)

    return redirect_url
 
def extract_article_text(url: str) -> dict:
    """Download an article page and extract its readable text."""

    validate_public_url(url)

    max_redirects = 5
    current_url = url

    for redirect_count in range(max_redirects + 1):
        response = requests.get(
            current_url,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; NewsChecker/0.1)"
            },
            allow_redirects=False,
        )

        if response.is_redirect or response.is_permanent_redirect:
            if redirect_count == max_redirects:
                raise ValueError("Too many redirects.")

            location = response.headers.get("Location")

            if not location:
                raise ValueError("Redirect response has no destination.")

            current_url = get_safe_redirect_url(current_url, location)
            continue

        response.raise_for_status()
        break

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

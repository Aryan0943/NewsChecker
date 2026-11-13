
import pytest
from pydantic import ValidationError

from app.schemas import ArticleRequest


def test_valid_url_request():
    request = ArticleRequest(
        content="https://example.com/news"
    )

    assert request.content == "https://example.com/news"


def test_valid_url_with_whitespace():
    request = ArticleRequest(
        content="  https://example.com/news  "
    )

    assert request.content == "https://example.com/news"


@pytest.mark.parametrize(
    "invalid_url",
    [
        "",
        "Example news article",
        "ftp://example.com/news",
        "www.example.com/news",
        "not-a-url",
    ],
)
def test_invalid_url_request(invalid_url):
    with pytest.raises(ValidationError):
        ArticleRequest(content=invalid_url)

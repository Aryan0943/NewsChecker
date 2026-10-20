
import pytest
from pydantic import ValidationError

from app.schemas import ArticleRequest


def test_valid_text_request():
    request = ArticleRequest(
        mode="text",
        content="Example news article",
    )

    assert request.mode == "text"
    assert request.content == "Example news article"


def test_valid_url_request():
    request = ArticleRequest(
        mode="url",
        content="https://example.com/news",
    )

    assert request.mode == "url"


def test_invalid_mode_is_rejected():
    with pytest.raises(ValidationError):
        ArticleRequest(
            mode="video",
            content="Example content",
        )


def test_empty_content_is_rejected():
    with pytest.raises(ValidationError):
        ArticleRequest(
            mode="text",
            content="   ",
        )


def test_content_over_limit_is_rejected():
    with pytest.raises(ValidationError):
        ArticleRequest(
            mode="text",
            content="a" * 20001,
        )

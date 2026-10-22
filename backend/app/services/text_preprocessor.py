
import re
def preprocess_article(text: str) -> str:
    """Clean article text before further processing."""

    # Remove leading and trailing whitespace.
    text = text.strip()

    # Replace consecutive whitespace characters with one space.
    text = re.sub(r"\s+", " ", text)

    return text

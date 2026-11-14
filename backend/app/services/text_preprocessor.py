import re


def preprocess_article(text: str) -> str:
    """Clean article text while preserving paragraph boundaries."""

    if not text:
        return ""

    # Normalize Windows and Mac line endings.
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove unnecessary spaces within each line.
    lines = [line.strip() for line in text.split("\n")]

    # Remove empty lines and preserve paragraph separation.
    text = "\n\n".join(line for line in lines if line)

    # Remove excessive spaces and tabs within paragraphs.
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()
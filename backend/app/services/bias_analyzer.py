
import logging

logger = logging.getLogger(__name__)


BIAS_CATEGORIES = [
    "political",
    "gender",
    "communal/caste",
    "cultural",
]


def analyze_bias(
    article_text: str,
    article_title: str = "",
) -> list[dict]:
    """
    Bias analysis interface.

    Current implementation:
        Placeholder until the custom ML model is integrated.

    Future implementation:
        1. Preprocess article text.
        2. Run the trained bias detection model.
        3. Generate category predictions.
        4. Extract relevant evidence spans.
        5. Return standardized results.

    The function's input and output contract should remain
    stable when the ML model is integrated.
    """

    if not article_text or not article_text.strip():
        raise ValueError("Article text cannot be empty.")

    logger.info(
        "Bias analysis requested. ML model is not integrated yet."
    )

    results = []

    for category in BIAS_CATEGORIES:
        results.append({
            "category": category,
            "status": "pending",
            "score": None,
            "explanation": (
                "Bias analysis model is under development "
                "and has not been integrated yet."
            ),
        })

    return results

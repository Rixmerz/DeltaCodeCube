"""Weak quantifier detection."""

import re

from bigcontext_mcp.tools.validators.constants import WEAK_QUANTIFIERS
from bigcontext_mcp.types import WeakQuantifierResult


def detect_weak_quantifiers(text: str) -> WeakQuantifierResult:
    """
    Detect weak quantifiers that require statistical evidence.

    Args:
        text: Text to analyze.

    Returns:
        WeakQuantifierResult with found quantifiers and recommendation.
    """
    found_quantifiers: list[str] = []

    for q in WEAK_QUANTIFIERS:
        term = q["term"]
        pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
        if pattern.search(text):
            found_quantifiers.append(term)

    if not found_quantifiers:
        return WeakQuantifierResult(
            quantifiers_found=[],
            recommendation="allow",
        )

    # Check for absolute quantifiers
    absolute_quantifiers = [
        q for q in found_quantifiers
        if any(wq["term"] == q and wq["strength"] == "absolute" for wq in WEAK_QUANTIFIERS)
    ]

    strong_quantifiers = [
        q for q in found_quantifiers
        if any(wq["term"] == q and wq["strength"] in ("strong", "absolute") for wq in WEAK_QUANTIFIERS)
    ]

    if absolute_quantifiers:
        recommendation = "block"
    elif strong_quantifiers:
        recommendation = "require_count"
    else:
        recommendation = "allow"

    return WeakQuantifierResult(
        quantifiers_found=found_quantifiers,
        recommendation=recommendation,
    )

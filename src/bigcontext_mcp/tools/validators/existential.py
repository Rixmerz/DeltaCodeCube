"""Existential response validation."""

import re

from bigcontext_mcp.types import ExistentialResponseResult


def validate_existential_response(response: str) -> ExistentialResponseResult:
    """
    Validate that a response to an existential question is properly formed.

    Valid responses are:
    - "YES" + textual evidence
    - "NO" + explicit denial

    Invalid responses are:
    - Meta-discourse about limitations
    - Hedging
    - Asking follow-up questions
    - Introducing categories not asked for

    Args:
        response: The response to validate.

    Returns:
        ExistentialResponseResult with validation status.
    """
    violations: list[str] = []

    # Check for YES/NO answer
    has_yes = bool(re.search(r"\byes\b", response, re.IGNORECASE))
    has_no = bool(re.search(r"\bno\b", response, re.IGNORECASE))
    has_answer = has_yes or has_no

    # Check for evidence (quotes, specific references)
    has_evidence = bool(
        re.search(r'[""].*[""]', response)  # Quoted text
        or re.search(r"\bverse\s+\d+", response, re.IGNORECASE)
        or re.search(r"\bchapter\s+\d+", response, re.IGNORECASE)
        or re.search(r"\b\d+:\d+\b", response)  # Bible verse format
    )

    # Check for meta-discourse violations
    meta_patterns = [
        r"\bI cannot\b",
        r"\bI am unable\b",
        r"\bI need more\b",
        r"\bI would need\b",
        r"\bit depends\b",
        r"\bmore context\b",
        r"\bclarify\b",
        r"\bdo you mean\b",
        r"\bwhat do you mean\b",
    ]
    for pattern in meta_patterns:
        if re.search(pattern, response, re.IGNORECASE):
            violations.append(f"Meta-discourse: {pattern}")

    # Check for hedging
    hedge_patterns = [
        r"\bpossibly\b",
        r"\bperhaps\b",
        r"\bmight be\b",
        r"\bcould be\b",
        r"\bit seems\b",
        r"\bappears to\b",
    ]
    for pattern in hedge_patterns:
        if re.search(pattern, response, re.IGNORECASE):
            violations.append(f"Hedging: {pattern}")

    # Check for questions
    if re.search(r"\?\s*$", response.strip()):
        violations.append("Response ends with question")

    is_valid = has_answer and (has_evidence or has_no) and len(violations) == 0

    return ExistentialResponseResult(
        is_valid=is_valid,
        has_answer=has_answer,
        has_evidence=has_evidence,
        violations=violations,
    )

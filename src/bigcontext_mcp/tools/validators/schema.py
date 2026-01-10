"""Extraction schema validation."""

import re

from bigcontext_mcp.types import ExtractionSchemaResult


def validate_extraction_schema(
    output: str,
    fields: list[str],
    allow_commentary: bool = False,
) -> ExtractionSchemaResult:
    """
    Validate that extraction output follows a strict schema.

    Args:
        output: The extraction output to validate.
        fields: Expected field names in output.
        allow_commentary: Whether commentary is allowed.

    Returns:
        ExtractionSchemaResult with validation status.
    """
    violations: list[str] = []
    has_commentary = False
    has_evaluative_language = False

    # Check for commentary patterns
    commentary_patterns = [
        r"\([^)]*note[^)]*\)",  # Parenthetical notes
        r"\([^)]*important[^)]*\)",
        r"\([^)]*interesting[^)]*\)",
        r"\bNote:\b",
        r"\bNotes:\b",
        r"\bCommentary:\b",
        r"\bObservation:\b",
    ]
    for pattern in commentary_patterns:
        if re.search(pattern, output, re.IGNORECASE):
            has_commentary = True
            if not allow_commentary:
                violations.append(f"Unauthorized commentary: {pattern}")

    # Check for evaluative language
    evaluative_patterns = [
        r"\binteresting(?:ly)?\b",
        r"\bimportant(?:ly)?\b",
        r"\bsignificant(?:ly)?\b",
        r"\bremarkab(?:le|ly)\b",
        r"\bnoteworth(?:y|ily)\b",
        r"\bsurprising(?:ly)?\b",
        r"\bstrik(?:ing|ingly)\b",
        r"\bbeautiful(?:ly)?\b",
        r"\bpowerful(?:ly)?\b",
    ]
    for pattern in evaluative_patterns:
        if re.search(pattern, output, re.IGNORECASE):
            has_evaluative_language = True
            violations.append(f"Evaluative language: {pattern}")

    # Check for expected fields (basic check)
    missing_fields = []
    for field in fields:
        # Check if field name appears (case-insensitive)
        if not re.search(rf"\b{re.escape(field)}\b", output, re.IGNORECASE):
            missing_fields.append(field)

    if missing_fields:
        violations.append(f"Missing fields: {', '.join(missing_fields)}")

    is_valid = len(violations) == 0

    return ExtractionSchemaResult(
        is_valid=is_valid,
        violations=violations,
        has_commentary=has_commentary,
        has_evaluative_language=has_evaluative_language,
    )

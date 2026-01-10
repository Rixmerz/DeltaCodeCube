"""Pattern contamination detection."""

import sqlite3

from bigcontext_mcp.db.queries import get_segment_by_id
from bigcontext_mcp.types import PatternContaminationResult


def detect_pattern_contamination(
    claimed_output: str,
    segment_id: int,
    conn: sqlite3.Connection,
    patterns: list[dict] | None = None,
) -> PatternContaminationResult:
    """
    Detect when output may be completing a known pattern not in source.

    Args:
        claimed_output: What the agent claims is in the text.
        segment_id: ID of the segment to check against.
        conn: Database connection.
        patterns: Optional pattern definitions (trigger, expected_completion).

    Returns:
        PatternContaminationResult with contamination status.
    """
    segment = get_segment_by_id(conn, segment_id)
    if not segment:
        return PatternContaminationResult(
            is_contaminated=False,
            pattern_name=None,
            expected_completion=None,
            actual_text=None,
        )

    content = segment["content"].lower()
    output_lower = claimed_output.lower()

    # Default patterns if none provided
    if patterns is None:
        patterns = [
            {
                "trigger": "and god said",
                "expected_completion": "and it was so",
                "description": "Genesis creation pattern",
            },
            {
                "trigger": "once upon a time",
                "expected_completion": "happily ever after",
                "description": "Fairy tale pattern",
            },
            {
                "trigger": "the court finds",
                "expected_completion": "in favor of",
                "description": "Legal ruling pattern",
            },
        ]

    for pattern in patterns:
        trigger = pattern.get("trigger", "").lower()
        expected = pattern.get("expected_completion", "").lower()

        # Check if trigger is in content
        if trigger and trigger in content:
            # Check if expected completion is in claimed output but NOT in content
            if expected and expected in output_lower and expected not in content:
                return PatternContaminationResult(
                    is_contaminated=True,
                    pattern_name=pattern.get("description", "Unknown pattern"),
                    expected_completion=expected,
                    actual_text=_find_actual_text(content, trigger),
                )

    return PatternContaminationResult(
        is_contaminated=False,
        pattern_name=None,
        expected_completion=None,
        actual_text=None,
    )


def _find_actual_text(content: str, trigger: str) -> str | None:
    """Find what actually follows the trigger in the content."""
    trigger_lower = trigger.lower()
    content_lower = content.lower()

    idx = content_lower.find(trigger_lower)
    if idx == -1:
        return None

    # Get the next 100 characters after the trigger
    start = idx + len(trigger)
    end = min(start + 100, len(content))
    return content[start:end].strip()[:50]  # Limit to 50 chars

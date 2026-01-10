"""Speaker identification in text."""

import re

from bigcontext_mcp.types import SpeakerIdentificationResult


def identify_speaker(
    content: str,
    priority_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    expected_speaker: str | None = None,
) -> SpeakerIdentificationResult:
    """
    Identify who is speaking in a text segment.

    Args:
        content: Text content to analyze.
        priority_patterns: Patterns to prioritize (e.g., ["God", "Lord"]).
        exclude_patterns: Patterns to flag as ambiguous.
        expected_speaker: Optional speaker to verify.

    Returns:
        SpeakerIdentificationResult with speaker and confidence.
    """
    evidence: list[str] = []
    speaker: str | None = None
    confidence = "unknown"

    # Speech verb patterns
    speech_patterns = [
        # "X said"
        re.compile(r"(\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:said|spoke|told|answered|replied|asked)", re.IGNORECASE),
        # "said X" (less common)
        re.compile(r"(?:said|spoke)\s+(\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", re.IGNORECASE),
        # "X declared" patterns
        re.compile(r"(\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:declared|proclaimed|announced)", re.IGNORECASE),
    ]

    candidates: list[str] = []

    for pattern in speech_patterns:
        for match in pattern.finditer(content):
            candidate = match.group(1).strip()
            if candidate:
                candidates.append(candidate)
                evidence.append(f"Speech pattern: {match.group()[:50]}")

    # Check priority patterns first
    if priority_patterns and candidates:
        for priority in priority_patterns:
            for candidate in candidates:
                if priority.lower() in candidate.lower():
                    speaker = candidate
                    confidence = "explicit"
                    break
            if speaker:
                break

    # If no priority match, use first candidate
    if not speaker and candidates:
        speaker = candidates[0]
        confidence = "contextual" if len(candidates) == 1 else "ambiguous"

    # Check exclude patterns
    if speaker and exclude_patterns:
        for exclude in exclude_patterns:
            if exclude.lower() in speaker.lower():
                confidence = "ambiguous"
                evidence.append(f"Excluded pattern matched: {exclude}")
                break

    # Check expected speaker
    is_expected = None
    if expected_speaker and speaker:
        is_expected = expected_speaker.lower() in speaker.lower()

    return SpeakerIdentificationResult(
        speaker=speaker,
        confidence=confidence,
        evidence=evidence[:5],
        is_expected_speaker=is_expected,
    )

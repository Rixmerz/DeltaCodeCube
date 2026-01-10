"""Text genre detection and divine agency detection."""

import re

from bigcontext_mcp.tools.validators.constants import (
    CAUSAL_ACTION_VERBS,
    SPEECH_VERB_WHITELIST,
    TEXT_GENRE_INDICATORS,
)
from bigcontext_mcp.types import DomainVocabulary, TextGenre, TextGenreResult


def detect_text_genre(
    content: str,
    vocabulary: DomainVocabulary | None = None,
) -> TextGenreResult:
    """
    Detect the genre of text based on structural patterns.

    Args:
        content: Text content to analyze.
        vocabulary: Optional domain-specific vocabulary.

    Returns:
        TextGenreResult with detected genre and indicators.
    """
    genre_scores: dict[str, int] = {
        "historical_narrative": 0,
        "narrative_poetry": 0,
        "prayer_praise": 0,
        "prophetic": 0,
        "recapitulation": 0,
    }
    indicators: list[str] = []

    # Check structural patterns
    for genre, patterns in TEXT_GENRE_INDICATORS.items():
        for pattern in patterns:
            matches = pattern.findall(content)
            if matches:
                genre_scores[genre] += len(matches)
                indicators.append(f"{genre}:{pattern.pattern[:30]}")

    # If vocabulary provided, check domain-specific indicators
    if vocabulary:
        if vocabulary.oracle_formulas:
            for formula in vocabulary.oracle_formulas:
                if formula.lower() in content.lower():
                    genre_scores["prophetic"] += 3
                    indicators.append(f"oracle_formula:{formula}")

        if vocabulary.praise_formulas:
            for formula in vocabulary.praise_formulas:
                if formula.lower() in content.lower():
                    genre_scores["prayer_praise"] += 3
                    indicators.append(f"praise_formula:{formula}")

    # Determine best match
    best_genre = max(genre_scores, key=lambda k: genre_scores[k])
    best_score = genre_scores[best_genre]

    if best_score == 0:
        return TextGenreResult(
            genre=TextGenre.UNKNOWN,
            confidence="low",
            indicators=[],
        )

    confidence = "high" if best_score >= 5 else "medium" if best_score >= 2 else "low"

    return TextGenreResult(
        genre=TextGenre(best_genre),
        confidence=confidence,
        indicators=indicators[:5],
    )


def detect_divine_agency_without_speech(
    content: str,
    agent_patterns: list[str] | None = None,
    vocabulary: DomainVocabulary | None = None,
) -> dict:
    """
    Detect when an agent acts WITHOUT speaking.

    Args:
        content: Text content to analyze.
        agent_patterns: Patterns to identify the agent.
        vocabulary: Optional domain-specific vocabulary.

    Returns:
        Dict with found status, agent, action verb, and whether speech was involved.
    """
    if not agent_patterns:
        return {
            "found": False,
            "agent": None,
            "action_verb": None,
            "has_speech_verb": False,
            "evidence": [],
        }

    # Find speech verbs
    speech_verbs_found: list[str] = []
    for verb in SPEECH_VERB_WHITELIST:
        if re.search(rf"\b{verb}\b", content, re.IGNORECASE):
            speech_verbs_found.append(verb)

    # Find action verbs with agents
    agent_found: str | None = None
    action_verb_found: str | None = None
    evidence: list[str] = []

    for agent_pattern in agent_patterns:
        escaped_agent = re.escape(agent_pattern)

        # Get action verbs to check
        verbs_to_check = list(CAUSAL_ACTION_VERBS)
        if vocabulary and vocabulary.narration_verbs:
            verbs_to_check.extend(vocabulary.narration_verbs)

        for verb in verbs_to_check:
            # Skip if this is also a speech verb
            if verb.lower() in [v.lower() for v in SPEECH_VERB_WHITELIST]:
                continue

            # Check for agent + verb pattern
            pattern = rf"\b(?:the\s+)?{escaped_agent}\s+(?:\w+\s+)?{re.escape(verb)}\b"
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                agent_found = agent_pattern
                action_verb_found = verb
                evidence.append(f"Found: {match.group()}")
                break

        if agent_found:
            break

    return {
        "found": agent_found is not None,
        "agent": agent_found,
        "action_verb": action_verb_found,
        "has_speech_verb": len(speech_verbs_found) > 0,
        "evidence": evidence,
    }

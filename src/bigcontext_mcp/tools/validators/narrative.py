"""Narrative voice and agency validation."""

import re

from bigcontext_mcp.tools.validators.constants import (
    CAUSAL_ACTION_VERBS,
    SPEECH_VERB_WHITELIST,
    STRUCTURAL_NARRATIVE_VOICE_PATTERNS,
)
from bigcontext_mcp.types import (
    AgencyExecutionResult,
    AgencyMode,
    DomainVocabulary,
    NarrativeVoiceResult,
    NarrativeVoiceType,
)


def detect_narrative_voice(
    content: str,
    vocabulary: DomainVocabulary | None = None,
) -> NarrativeVoiceResult:
    """
    Detect the narrative voice type in text.

    Args:
        content: Text content to analyze.
        vocabulary: Optional domain-specific vocabulary for enhanced detection.

    Returns:
        NarrativeVoiceResult with voice type and evidence.
    """
    indicators: list[str] = []
    voice_scores: dict[str, int] = {
        "primary_narration": 0,
        "human_to_divine": 0,
        "divine_direct_speech": 0,
        "human_about_divine": 0,
    }

    # Check structural patterns
    for voice_type, patterns in STRUCTURAL_NARRATIVE_VOICE_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(content):
                voice_scores[voice_type] += 1
                indicators.append(f"structural:{voice_type}")

    # If vocabulary provided, check domain-specific patterns
    if vocabulary:
        patterns = _generate_domain_patterns(vocabulary)
        for voice_type, domain_patterns in patterns.items():
            for pattern in domain_patterns:
                if pattern.search(content):
                    voice_scores[voice_type] += 2  # Higher weight for domain patterns
                    indicators.append(f"domain:{voice_type}")

    # Determine best match
    best_type = max(voice_scores, key=lambda k: voice_scores[k])
    best_score = voice_scores[best_type]

    if best_score == 0:
        return NarrativeVoiceResult(
            voice_type=NarrativeVoiceType.UNKNOWN,
            confidence="low",
            evidence=[],
            is_retrospective=False,
        )

    # Calculate confidence
    confidence = "high" if best_score >= 3 else "medium" if best_score >= 2 else "low"

    # Check for retrospective
    is_retrospective = best_type == "human_to_divine" or "recapitulation" in indicators

    return NarrativeVoiceResult(
        voice_type=NarrativeVoiceType(best_type),
        confidence=confidence,
        evidence=indicators[:5],  # Limit to 5 indicators
        is_retrospective=is_retrospective,
    )


def validate_agency_execution(
    content: str,
    agent_patterns: list[str] | None = None,
    vocabulary: DomainVocabulary | None = None,
) -> AgencyExecutionResult:
    """
    Validate whether an action is EXECUTED in-scene vs merely REFERENCED.

    Args:
        content: Text content to analyze.
        agent_patterns: Patterns to identify the agent (e.g., ["God", "Lord"]).
        vocabulary: Optional domain-specific vocabulary.

    Returns:
        AgencyExecutionResult with execution status and mode.
    """
    evidence: list[str] = []
    agent: str | None = None
    action: str | None = None

    # First detect narrative voice
    voice_result = detect_narrative_voice(content, vocabulary)

    # If human_to_divine, action is retrospective
    if voice_result.voice_type == NarrativeVoiceType.HUMAN_TO_DIVINE:
        return AgencyExecutionResult(
            is_executed=False,
            mode=AgencyMode.RETROSPECTIVE,
            agent=None,
            action=None,
            evidence=["Voice type: human_to_divine (retrospective prayer/praise)"],
            warning="Action is recalled, not executed in-scene",
        )

    # Check for action verbs
    action_verbs_found: list[str] = []
    speech_verbs_found: list[str] = []

    for verb in CAUSAL_ACTION_VERBS:
        if re.search(rf"\b{verb}\b", content, re.IGNORECASE):
            action_verbs_found.append(verb)

    for verb in SPEECH_VERB_WHITELIST:
        if re.search(rf"\b{verb}\b", content, re.IGNORECASE):
            speech_verbs_found.append(verb)

    # Check for specific agent if patterns provided
    if agent_patterns:
        for agent_pattern in agent_patterns:
            escaped_agent = re.escape(agent_pattern)
            for verb in action_verbs_found:
                # Pattern: "Agent + verb" or "the Agent + verb"
                pattern = rf"\b(?:the\s+)?{escaped_agent}\s+(?:\w+\s+)?{verb}\b"
                if re.search(pattern, content, re.IGNORECASE):
                    agent = agent_pattern
                    action = verb
                    evidence.append(f"Found: {agent} {verb}")
                    break
            if agent:
                break

    # Determine mode
    if voice_result.voice_type == NarrativeVoiceType.PRIMARY_NARRATION:
        mode = AgencyMode.EXECUTED
        is_executed = True
    elif action_verbs_found and not speech_verbs_found:
        mode = AgencyMode.EXECUTED
        is_executed = True
        evidence.append("Action verb without speech verb")
    else:
        mode = AgencyMode.UNKNOWN
        is_executed = False

    return AgencyExecutionResult(
        is_executed=is_executed,
        mode=mode,
        agent=agent,
        action=action,
        evidence=evidence,
        warning=None,
    )


def _generate_domain_patterns(vocabulary: DomainVocabulary) -> dict[str, list[re.Pattern]]:
    """Generate domain-specific patterns from vocabulary."""
    patterns: dict[str, list[re.Pattern]] = {
        "primary_narration": [],
        "human_to_divine": [],
        "divine_direct_speech": [],
        "human_about_divine": [],
    }

    if not vocabulary:
        return patterns

    escape = lambda s: re.escape(s)

    # Generate agent-based patterns
    if vocabulary.agents:
        agent_group = "|".join(escape(a) for a in vocabulary.agents)

        if vocabulary.narration_verbs:
            verb_group = "|".join(escape(v) for v in vocabulary.narration_verbs)
            patterns["primary_narration"].extend([
                re.compile(rf"\b(?:the\s+)?(?:{agent_group})\s+(?:{verb_group})\b", re.IGNORECASE),
                re.compile(rf"\band\s+(?:the\s+)?(?:{agent_group})\s+(?:{verb_group})\b", re.IGNORECASE),
            ])

    # Generate addressee patterns
    if vocabulary.addressees:
        addressee_group = "|".join(escape(a) for a in vocabulary.addressees)

        if vocabulary.action_verbs:
            verb_group = "|".join(escape(v) for v in vocabulary.action_verbs)
            patterns["human_to_divine"].extend([
                re.compile(rf"\byou\s+(?:{verb_group})", re.IGNORECASE),
                re.compile(rf"\b(?:O|oh)\s+(?:{addressee_group})", re.IGNORECASE),
            ])

    return patterns

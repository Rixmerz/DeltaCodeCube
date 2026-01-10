"""Constants for extraction validators."""

import re

# ============================================================================
# SPEECH VERBS (indicate speaking/communication)
# ============================================================================

SPEECH_VERB_WHITELIST = frozenset([
    # English - explicit speech acts
    "said", "spoke", "speak", "speaks", "told", "tell", "tells",
    "called", "call", "calls", "answered", "answer", "answers",
    "replied", "reply", "replies", "asked", "ask", "asks",
    "declared", "declare", "declares", "proclaimed", "proclaim", "proclaims",
    "announced", "announce", "announces", "cried", "cry", "cries",
    "shouted", "shout", "shouts", "whispered", "whisper", "whispers",
    "commanded", "command", "commands", "ordered", "order", "orders",
    "instructed", "instruct", "instructs", "warned", "warn", "warns",
    "promised", "promise", "promises", "swore", "swear", "swears",
    "blessed", "bless", "blesses", "cursed", "curse", "curses",
    "prayed", "pray", "prays", "prophesied", "prophesy", "prophesies",
    "testified", "testify", "testifies", "confessed", "confess", "confesses",
    "sang", "sing", "sings", "recited", "recite", "recites",
    # Spanish
    "dijo", "dice", "habló", "habla", "respondió", "responde",
    "preguntó", "pregunta", "declaró", "declara", "proclamó", "proclama",
])

# ============================================================================
# CAUSAL/ACTION VERBS (action/causation WITHOUT speech)
# ============================================================================

CAUSAL_ACTION_VERBS = frozenset([
    # English - causation/creation verbs
    "caused", "cause", "causes", "made", "make", "makes",
    "created", "create", "creates", "formed", "form", "forms",
    "sent", "send", "sends", "brought", "bring", "brings",
    "gave", "give", "gives", "took", "take", "takes",
    "led", "lead", "leads", "drove", "drive", "drives",
    "moved", "move", "moves", "carried", "carry", "carries",
    "placed", "place", "places", "put", "puts",
    "raised", "raise", "raises", "lifted", "lift", "lifts",
    "lowered", "lower", "lowers", "opened", "open", "opens",
    "closed", "close", "closes", "divided", "divide", "divides",
    "gathered", "gather", "gathers", "scattered", "scatter", "scatters",
    "remembered", "remember", "remembers", "forgot", "forget", "forgets",
    "saved", "save", "saves", "delivered", "deliver", "delivers",
    "healed", "heal", "heals", "struck", "strike", "strikes",
    "killed", "kill", "kills", "destroyed", "destroy", "destroys",
    "built", "build", "builds", "established", "establish", "establishes",
    "rained", "rain", "rains", "fed", "feed", "feeds",
    "provided", "provide", "provides", "protected", "protect", "protects",
    "guided", "guide", "guides", "judged", "judge", "judges",
    # Spanish
    "causó", "causa", "hizo", "hace", "creó", "crea",
    "envió", "envía", "trajo", "trae", "dio", "da",
    "llevó", "lleva", "guió", "guía", "salvó", "salva",
])

# ============================================================================
# STRUCTURAL NARRATIVE VOICE PATTERNS (pure grammar, no vocabulary)
# ============================================================================

STRUCTURAL_NARRATIVE_VOICE_PATTERNS = {
    "human_to_divine": [
        # Second person addressing pattern
        re.compile(r"\b(?:you|thou)\s+\w+", re.IGNORECASE),
        re.compile(r"\b(?:you|thou)\s+(?:are|have been|were)\s+(?:my|our)\s+\w+", re.IGNORECASE),
        re.compile(r"\bO\s+\w+", re.IGNORECASE),  # Vocative address
        re.compile(r"\bpraise\s+(?:you|the\s+\w+)", re.IGNORECASE),
        re.compile(r"\bthank\s+(?:you|the\s+\w+)", re.IGNORECASE),
        re.compile(r"\bI\s+(?:call|cry|pray|lift)\s+(?:to|unto)\s+(?:you|the\s+\w+)", re.IGNORECASE),
        # Spanish equivalents
        re.compile(r"\btú\s+\w+", re.IGNORECASE),
        re.compile(r"\boh\s+\w+", re.IGNORECASE),
    ],
    "primary_narration": [
        # Sequential narrative markers
        re.compile(r"\bthen\s+\w+\s+\w+", re.IGNORECASE),
        re.compile(r"\band\s+\w+\s+\w+", re.IGNORECASE),
        re.compile(r"\bso\s+\w+\s+\w+", re.IGNORECASE),
        re.compile(r"\bafter\s+(?:this|that)\s+\w+\s+\w+", re.IGNORECASE),
        # Past tense action patterns
        re.compile(r"\b\w+ed\s+(?:the|a|an|his|her|their)\s+\w+", re.IGNORECASE),
    ],
    "divine_direct_speech": [
        # First person divine declarations
        re.compile(r'\b(?:I\s+am|I\s+will|I\s+have|I\s+shall)\b', re.IGNORECASE),
        re.compile(r'\bLet\s+there\s+be\b', re.IGNORECASE),
        re.compile(r'\bBehold,?\s+I\b', re.IGNORECASE),
    ],
    "human_about_divine": [
        # Third person divine descriptions
        re.compile(r"\b(?:he|she|it)\s+is\s+(?:my|our|the)\s+\w+", re.IGNORECASE),
        re.compile(r"\bthe\s+\w+\s+is\s+\w+", re.IGNORECASE),
    ],
}

# ============================================================================
# TEXT GENRE INDICATORS
# ============================================================================

TEXT_GENRE_INDICATORS = {
    "historical_narrative": [
        re.compile(r"\bthen\s+\w+\s+(?:did|made|went|came)", re.IGNORECASE),
        re.compile(r"\band\s+it\s+(?:came to pass|happened)", re.IGNORECASE),
        re.compile(r"\bin\s+(?:the|those)\s+days", re.IGNORECASE),
        re.compile(r"\bat\s+that\s+time", re.IGNORECASE),
    ],
    "narrative_poetry": [
        re.compile(r"^[A-Z].*\n[A-Z]", re.MULTILINE),  # Poetic line structure
        re.compile(r"\bO\s+\w+", re.IGNORECASE),  # Vocative
        re.compile(r"\bSelah\b", re.IGNORECASE),  # Psalm marker
    ],
    "prayer_praise": [
        re.compile(r"\bpraise\b", re.IGNORECASE),
        re.compile(r"\bthank\s+(?:you|the)", re.IGNORECASE),
        re.compile(r"\bblessed\s+(?:be|is)", re.IGNORECASE),
        re.compile(r"\bhallelu", re.IGNORECASE),
    ],
    "prophetic": [
        re.compile(r"\bthus\s+says\b", re.IGNORECASE),
        re.compile(r"\bthe\s+word\s+of\s+the\b", re.IGNORECASE),
        re.compile(r"\bdeclares\s+the\b", re.IGNORECASE),
        re.compile(r"\bwoe\s+(?:to|unto)\b", re.IGNORECASE),
    ],
    "recapitulation": [
        re.compile(r"\byou\s+(?:led|brought|gave|made|saved|delivered)", re.IGNORECASE),
        re.compile(r"\bremember\s+(?:how|when|that)", re.IGNORECASE),
        re.compile(r"\bour\s+(?:fathers|ancestors)", re.IGNORECASE),
    ],
}

# ============================================================================
# WEAK QUANTIFIERS
# ============================================================================

WEAK_QUANTIFIERS = [
    # Frequency quantifiers (require evidence)
    {"term": "frequently", "strength": "strong", "requires_evidence": True},
    {"term": "often", "strength": "strong", "requires_evidence": True},
    {"term": "typically", "strength": "strong", "requires_evidence": True},
    {"term": "usually", "strength": "strong", "requires_evidence": True},
    {"term": "generally", "strength": "strong", "requires_evidence": True},
    {"term": "commonly", "strength": "strong", "requires_evidence": True},
    {"term": "rarely", "strength": "strong", "requires_evidence": True},
    {"term": "seldom", "strength": "strong", "requires_evidence": True},
    # Universal quantifiers (often unsupported)
    {"term": "always", "strength": "absolute", "requires_evidence": True},
    {"term": "never", "strength": "absolute", "requires_evidence": True},
    {"term": "every", "strength": "absolute", "requires_evidence": True},
    {"term": "all", "strength": "absolute", "requires_evidence": True},
    {"term": "none", "strength": "absolute", "requires_evidence": True},
    # Vague quantifiers
    {"term": "many", "strength": "vague", "requires_evidence": True},
    {"term": "most", "strength": "vague", "requires_evidence": True},
    {"term": "some", "strength": "vague", "requires_evidence": False},
    {"term": "few", "strength": "vague", "requires_evidence": False},
    {"term": "several", "strength": "vague", "requires_evidence": False},
]

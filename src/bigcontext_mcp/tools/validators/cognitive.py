"""Cognitive operation validation tools."""

import re
import sqlite3

from bigcontext_mcp.db.queries import get_segment_by_id
from bigcontext_mcp.types import (
    CognitiveAuditResult,
    InferenceViolationResult,
    PermittedOperationsResult,
    SafeFallbackResult,
)


# Unauthorized operation patterns
UNAUTHORIZED_OPERATIONS = {
    "synthesis": [
        r"\bsynthesize\b",
        r"\bcombine.*meaning\b",
        r"\bunified.*view\b",
        r"\boverall.*message\b",
    ],
    "explanation": [
        r"\bexplain\s+why\b",
        r"\bthe\s+reason\s+(is|was)\b",
        r"\bthis\s+means\b",
        r"\bwhat.*means\b",
    ],
    "causality": [
        r"\bcaused\s+by\b",
        r"\bresulted\s+in\b",
        r"\bled\s+to\b",
        r"\bbecause\b.*\btherefore\b",
    ],
    "teleology": [
        r"\bpurpose\s+(is|was)\b",
        r"\bintended\s+to\b",
        r"\bin\s+order\s+to\b",
        r"\bso\s+that\b.*\bcould\b",
    ],
    "cross_section": [
        r"\bthroughout\s+(the\s+)?bible\b",
        r"\bin\s+all\s+of\s+scripture\b",
        r"\bbiblical\s+theology\b",
        r"\bcanonical\s+reading\b",
    ],
}


def audit_cognitive_operations(
    document_id: int,
    query: str,
    planned_output: str,
    conn: sqlite3.Connection,
) -> CognitiveAuditResult:
    """
    Validate that query and planned output comply with cognitive constraints.

    Detects unauthorized operations (synthesis, explanation, causality inference).

    Args:
        document_id: ID of the document being queried.
        query: The user query to analyze.
        planned_output: The planned response text to validate.
        conn: Database connection.

    Returns:
        CognitiveAuditResult with compliance status.
    """
    violations: list[dict] = []
    query_lower = query.lower()
    output_lower = planned_output.lower()

    for operation_type, patterns in UNAUTHORIZED_OPERATIONS.items():
        for pattern in patterns:
            # Check query
            if re.search(pattern, query_lower):
                violations.append({
                    "type": operation_type,
                    "location": "query",
                    "pattern": pattern,
                    "match": re.search(pattern, query_lower).group(0) if re.search(pattern, query_lower) else None,
                })
            # Check output
            if re.search(pattern, output_lower):
                violations.append({
                    "type": operation_type,
                    "location": "output",
                    "pattern": pattern,
                    "match": re.search(pattern, output_lower).group(0) if re.search(pattern, output_lower) else None,
                })

    is_compliant = len(violations) == 0

    safe_fallback: str | None = None
    if not is_compliant:
        violation_types = set(v["type"] for v in violations)
        safe_fallback = f"Cannot perform {', '.join(violation_types)} on this document"

    return CognitiveAuditResult(
        is_compliant=is_compliant,
        violations=violations,
        safe_fallback=safe_fallback,
    )


def detect_inference_violations(
    text: str,
) -> InferenceViolationResult:
    """
    Scan text for inferential connectors and prohibited abstract nouns.

    Detects: therefore, thus, implies, means that, ontology, mechanism, structure.

    Args:
        text: The text to scan for inference violations.

    Returns:
        InferenceViolationResult with detected violations.
    """
    text_lower = text.lower()

    # Inferential connectors
    connectors = [
        "therefore",
        "thus",
        "hence",
        "consequently",
        "implies",
        "implies that",
        "means that",
        "it follows",
        "we can conclude",
        "this shows",
        "this proves",
        "this demonstrates",
    ]

    # Prohibited abstract nouns
    abstract_nouns = [
        "ontology",
        "mechanism",
        "structure",
        "essence",
        "substance",
        "metaphysics",
        "epistemology",
        "teleology",
        "causality",
        "modality",
    ]

    found_connectors: list[str] = []
    found_abstract_nouns: list[str] = []

    for connector in connectors:
        if connector in text_lower:
            found_connectors.append(connector)

    for noun in abstract_nouns:
        if noun in text_lower:
            found_abstract_nouns.append(noun)

    has_violations = len(found_connectors) > 0 or len(found_abstract_nouns) > 0

    return InferenceViolationResult(
        has_violations=has_violations,
        connectors_found=found_connectors,
        abstract_nouns_found=found_abstract_nouns,
    )


def get_permitted_operations(
    segment_id: int,
    conn: sqlite3.Connection,
) -> PermittedOperationsResult:
    """
    Get list of permitted cognitive operations based on text genre.

    Different genres allow different operations:
    - Narrative: sequence, agency, speech acts
    - Poetry: parallelism, imagery, emotion
    - Wisdom: proverbs, observations
    - Prophecy: oracles, visions
    - Epistle: argument, exhortation
    - Apocalyptic: symbolism, visions
    - Law: commands, statutes
    - Genealogy: lineage, relationships

    Args:
        segment_id: ID of the segment to check.
        conn: Database connection.

    Returns:
        PermittedOperationsResult with allowed operations.
    """
    segment = get_segment_by_id(conn, segment_id)
    if not segment:
        return PermittedOperationsResult(
            genre="unknown",
            permitted_operations=[],
            prohibited_operations=list(UNAUTHORIZED_OPERATIONS.keys()),
        )

    content = segment["content"].lower()

    # Simple genre detection
    genre = "narrative"  # default

    if any(marker in content for marker in ["thus says", "oracle", "vision"]):
        genre = "prophecy"
    elif any(marker in content for marker in ["blessed is", "wisdom", "proverb"]):
        genre = "wisdom"
    elif any(marker in content for marker in ["dear", "grace to you", "brethren"]):
        genre = "epistle"
    elif any(marker in content for marker in ["beast", "dragon", "seven seals"]):
        genre = "apocalyptic"
    elif any(marker in content for marker in ["thou shalt", "commandment", "statute"]):
        genre = "law"
    elif any(marker in content for marker in ["son of", "begat", "generations"]):
        genre = "genealogy"
    elif any(marker in content for marker in ["selah", "psalm", "praise"]):
        genre = "poetry"

    # Operations by genre
    genre_operations = {
        "narrative": ["sequence_extraction", "agency_identification", "speech_act_detection"],
        "poetry": ["parallelism_analysis", "imagery_extraction", "emotion_detection"],
        "wisdom": ["proverb_extraction", "observation_listing"],
        "prophecy": ["oracle_extraction", "vision_description"],
        "epistle": ["argument_tracing", "exhortation_listing"],
        "apocalyptic": ["symbol_listing", "vision_description"],
        "law": ["command_extraction", "statute_listing"],
        "genealogy": ["lineage_tracing", "relationship_mapping"],
    }

    permitted = genre_operations.get(genre, [])

    # All genres prohibit cross-section synthesis
    prohibited = ["synthesis", "cross_section", "explanation"]

    return PermittedOperationsResult(
        genre=genre,
        permitted_operations=permitted,
        prohibited_operations=prohibited,
    )


def generate_safe_fallback(
    question_type: str,
    document_title: str,
) -> SafeFallbackResult:
    """
    Generate a safe, compliant response when a query requires unauthorized operations.

    Args:
        question_type: The type of unauthorized operation requested.
        document_title: Title of the document for the fallback message.

    Returns:
        SafeFallbackResult with safe response.
    """
    fallbacks = {
        "synthesis": (
            f"I cannot synthesize meaning across {document_title}. "
            "I can only extract specific patterns from individual segments. "
            "Please ask about specific passages."
        ),
        "explanation": (
            f"I cannot explain why something appears in {document_title}. "
            "I can only report what is textually present. "
            "Please ask what the text says, not what it means."
        ),
        "causality": (
            f"I cannot infer causal relationships in {document_title}. "
            "I can only report sequences and stated relationships. "
            "Please ask about what follows what, not why."
        ),
        "teleology": (
            f"I cannot determine purposes or intentions in {document_title}. "
            "I can only report stated purposes if present. "
            "Please ask about explicit statements of purpose."
        ),
        "cross_section": (
            f"I cannot make claims across all of {document_title}. "
            "I can only analyze specific segments. "
            "Please specify which passage you want to examine."
        ),
    }

    response = fallbacks.get(
        question_type,
        f"I cannot perform this operation on {document_title}. Please reformulate your question."
    )

    return SafeFallbackResult(
        question_type=question_type,
        safe_response=response,
        suggestion="Reformulate as an extraction query targeting specific text",
    )

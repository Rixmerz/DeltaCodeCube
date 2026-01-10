"""Epistemological analysis tools."""

import sqlite3

from bigcontext_mcp.db.queries import get_document_by_id, get_segment_by_id
from bigcontext_mcp.types import (
    SourceCapabilitiesResult,
    ClaimValidationResult,
    EpistemologicalReportResult,
    LanguageOperationResult,
)


def get_source_capabilities(
    document_id: int,
    conn: sqlite3.Connection,
) -> SourceCapabilitiesResult:
    """
    Analyze what a document CAN and CANNOT support for grounded claims.

    Returns detected languages, whether original Hebrew/Greek/Aramaic is present,
    textual variant availability, and epistemological limitations.

    Args:
        document_id: ID of the document to analyze.
        conn: Database connection.

    Returns:
        SourceCapabilitiesResult with capability analysis.
    """
    doc = get_document_by_id(conn, document_id)
    if not doc:
        return SourceCapabilitiesResult(
            document_id=document_id,
            detected_languages=[],
            has_original_languages=False,
            has_textual_variants=False,
            has_critical_apparatus=False,
            limitations=[],
            supported_claims=[],
            unsupported_claims=[],
        )

    content = doc.get("content", "") or ""
    content_lower = content.lower()

    # Detect languages
    detected_languages: list[str] = []
    limitations: list[str] = []
    supported_claims: list[str] = []
    unsupported_claims: list[str] = []

    # Check for Hebrew characters
    has_hebrew = any("\u0590" <= c <= "\u05FF" for c in content)
    if has_hebrew:
        detected_languages.append("hebrew")
        supported_claims.append("Hebrew root analysis")
    else:
        limitations.append("No Hebrew text present")
        unsupported_claims.append("Hebrew morphology claims")

    # Check for Greek characters
    has_greek = any("\u0370" <= c <= "\u03FF" or "\u1F00" <= c <= "\u1FFF" for c in content)
    if has_greek:
        detected_languages.append("greek")
        supported_claims.append("Greek word analysis")
    else:
        limitations.append("No Greek text present")
        unsupported_claims.append("Greek morphology claims")

    # Check for Aramaic (uses Hebrew script mostly)
    has_aramaic = has_hebrew and any(
        marker in content_lower
        for marker in ["aramaic", "chaldean", "syriac"]
    )
    if has_aramaic:
        detected_languages.append("aramaic")

    # Check for textual variants
    has_variants = any(
        marker in content_lower
        for marker in [
            "variant",
            "manuscript",
            "codex",
            "textual criticism",
            "apparatus",
            "ms.",
            "mss.",
        ]
    )

    # Check for critical apparatus
    has_apparatus = any(
        marker in content_lower
        for marker in [
            "critical apparatus",
            "nestle-aland",
            "ubs",
            "textual notes",
            "variant reading",
        ]
    )

    if has_variants:
        supported_claims.append("Textual variant awareness")
    else:
        unsupported_claims.append("Manuscript comparison claims")

    if has_apparatus:
        supported_claims.append("Critical text analysis")
    else:
        limitations.append("No critical apparatus present")
        unsupported_claims.append("Text-critical claims")

    # English is default if no original languages
    if not has_hebrew and not has_greek:
        detected_languages.append("english")
        limitations.append("Translation only - no access to original languages")

    has_original = has_hebrew or has_greek

    return SourceCapabilitiesResult(
        document_id=document_id,
        detected_languages=detected_languages,
        has_original_languages=has_original,
        has_textual_variants=has_variants,
        has_critical_apparatus=has_apparatus,
        limitations=limitations,
        supported_claims=supported_claims,
        unsupported_claims=unsupported_claims,
    )


def validate_claim(
    document_id: int,
    claim: str,
    conn: sqlite3.Connection,
) -> ClaimValidationResult:
    """
    Check if a specific claim can be grounded in the source document.

    Args:
        document_id: ID of the document to validate against.
        claim: The claim or assertion to validate.
        conn: Database connection.

    Returns:
        ClaimValidationResult with validation status.
    """
    capabilities = get_source_capabilities(document_id, conn)
    claim_lower = claim.lower()

    requires_capability: str | None = None
    is_valid = True
    reason: str | None = None

    # Check Hebrew claims
    hebrew_markers = ["hebrew", "root", "qnh", "bara", "elohim", "yhwh"]
    if any(marker in claim_lower for marker in hebrew_markers):
        requires_capability = "hebrew"
        if "hebrew" not in capabilities.detected_languages:
            is_valid = False
            reason = "Claim requires Hebrew text not present in document"

    # Check Greek claims
    greek_markers = ["greek", "logos", "theos", "pneuma", "christos"]
    if any(marker in claim_lower for marker in greek_markers):
        requires_capability = "greek"
        if "greek" not in capabilities.detected_languages:
            is_valid = False
            reason = "Claim requires Greek text not present in document"

    # Check manuscript claims
    manuscript_markers = ["manuscript", "codex", "variant", "textual"]
    if any(marker in claim_lower for marker in manuscript_markers):
        requires_capability = "textual_variants"
        if not capabilities.has_textual_variants:
            is_valid = False
            reason = "Claim requires textual variant data not present"

    # Check critical apparatus claims
    critical_markers = ["apparatus", "nestle", "ubs", "critical text"]
    if any(marker in claim_lower for marker in critical_markers):
        requires_capability = "critical_apparatus"
        if not capabilities.has_critical_apparatus:
            is_valid = False
            reason = "Claim requires critical apparatus not present"

    return ClaimValidationResult(
        is_valid=is_valid,
        claim=claim,
        requires_capability=requires_capability,
        document_has_capability=is_valid,
        reason=reason,
    )


def get_epistemological_report(
    document_id: int,
    query: str,
    conn: sqlite3.Connection,
) -> EpistemologicalReportResult:
    """
    Generate a complete epistemological analysis before making scholarly claims.

    Args:
        document_id: ID of the document to analyze.
        query: The research question or claim being investigated.
        conn: Database connection.

    Returns:
        EpistemologicalReportResult with comprehensive analysis.
    """
    capabilities = get_source_capabilities(document_id, conn)
    claim_result = validate_claim(document_id, query, conn)

    # Detect language hard stops
    language_hard_stops: list[str] = []
    if "hebrew" in query.lower() and "hebrew" not in capabilities.detected_languages:
        language_hard_stops.append("Hebrew analysis blocked: no Hebrew text")
    if "greek" in query.lower() and "greek" not in capabilities.detected_languages:
        language_hard_stops.append("Greek analysis blocked: no Greek text")

    # Detect canonical frame
    canonical_frame: str | None = None
    query_lower = query.lower()
    if any(term in query_lower for term in ["trinity", "trinitarian"]):
        canonical_frame = "Trinitarian (post-Nicene doctrine)"
    elif any(term in query_lower for term in ["emanation", "neoplatonic"]):
        canonical_frame = "Neoplatonic metaphysics"
    elif any(term in query_lower for term in ["cause", "causality", "aristotelian"]):
        canonical_frame = "Aristotelian causality"

    # Auto-critique
    auto_critique: list[str] = []
    if canonical_frame:
        auto_critique.append(f"Query imports {canonical_frame} - may distort text-internal meaning")
    if not capabilities.has_original_languages:
        auto_critique.append("Translation layer prevents morphological analysis")
    if not capabilities.has_textual_variants:
        auto_critique.append("Cannot assess textual stability")

    # Confidence decay
    confidence_decay = 1.0
    if not capabilities.has_original_languages:
        confidence_decay *= 0.7
    if canonical_frame:
        confidence_decay *= 0.8
    if language_hard_stops:
        confidence_decay *= 0.5

    # Recommendations
    recommendations: list[str] = []
    if language_hard_stops:
        recommendations.append("Obtain original language texts before proceeding")
    if canonical_frame:
        recommendations.append("Reformulate query using text-internal categories")
    if confidence_decay < 0.5:
        recommendations.append("Consider limiting claims to text-observable patterns only")

    return EpistemologicalReportResult(
        document_id=document_id,
        query=query,
        language_hard_stops=language_hard_stops,
        canonical_frame=canonical_frame,
        auto_critique=auto_critique,
        confidence_decay=confidence_decay,
        recommendations=recommendations,
        capabilities=capabilities,
    )


def check_language_operation(
    document_id: int,
    operation: str,
    language: str,
    conn: sqlite3.Connection,
) -> LanguageOperationResult:
    """
    Check if a specific linguistic operation is allowed.

    Args:
        document_id: ID of the document.
        operation: The operation to check (e.g., "root analysis").
        language: The language involved (hebrew, greek, aramaic).
        conn: Database connection.

    Returns:
        LanguageOperationResult with permission status.
    """
    capabilities = get_source_capabilities(document_id, conn)

    is_allowed = language.lower() in [lang.lower() for lang in capabilities.detected_languages]

    reason: str | None = None
    alternative: str | None = None

    if not is_allowed:
        reason = f"Document lacks {language} text required for {operation}"
        alternative = f"Use English translation analysis instead of {language} {operation}"

    return LanguageOperationResult(
        is_allowed=is_allowed,
        operation=operation,
        language=language,
        reason=reason,
        alternative=alternative,
    )

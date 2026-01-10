"""Literal quote validation."""

import sqlite3
from difflib import SequenceMatcher

from bigcontext_mcp.db.queries import get_segment_by_id
from bigcontext_mcp.types import LiteralQuoteResult


def validate_literal_quote(
    conn: sqlite3.Connection,
    quote: str,
    segment_id: int | None = None,
    document_id: int | None = None,
    fuzzy_threshold: float = 0.8,
) -> LiteralQuoteResult:
    """
    Validate that a quote exists EXACTLY in the source.

    Args:
        conn: Database connection.
        quote: The quote to validate.
        segment_id: Optional segment ID to check.
        document_id: Optional document ID to check.
        fuzzy_threshold: Similarity threshold for partial matches.

    Returns:
        LiteralQuoteResult with confidence level.
    """
    quote_normalized = _normalize_text(quote)

    # If segment_id provided, check that segment
    if segment_id:
        segment = get_segment_by_id(conn, segment_id)
        if not segment:
            return LiteralQuoteResult(
                confidence="not_found",
                matched_text=None,
                similarity=None,
            )

        content = segment["content"]
        content_normalized = _normalize_text(content)

        # Check for exact match
        if quote_normalized in content_normalized:
            return LiteralQuoteResult(
                confidence="textual",
                matched_text=quote,
                similarity=1.0,
            )

        # Check for partial match
        similarity = _calculate_similarity(quote_normalized, content_normalized)
        if similarity >= fuzzy_threshold:
            return LiteralQuoteResult(
                confidence="partial",
                matched_text=_find_best_match(quote_normalized, content),
                similarity=similarity,
            )

        return LiteralQuoteResult(
            confidence="not_found",
            matched_text=None,
            similarity=similarity,
        )

    # If document_id provided, search all segments
    if document_id:
        cursor = conn.execute(
            "SELECT id, content FROM segments WHERE document_id = ?",
            (document_id,),
        )
        segments = cursor.fetchall()

        best_similarity = 0.0
        best_match = None

        for seg in segments:
            content = seg["content"]
            content_normalized = _normalize_text(content)

            if quote_normalized in content_normalized:
                return LiteralQuoteResult(
                    confidence="textual",
                    matched_text=quote,
                    similarity=1.0,
                )

            similarity = _calculate_similarity(quote_normalized, content_normalized)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = _find_best_match(quote_normalized, content)

        if best_similarity >= fuzzy_threshold:
            return LiteralQuoteResult(
                confidence="partial",
                matched_text=best_match,
                similarity=best_similarity,
            )

        return LiteralQuoteResult(
            confidence="not_found",
            matched_text=None,
            similarity=best_similarity if best_similarity > 0 else None,
        )

    return LiteralQuoteResult(
        confidence="not_found",
        matched_text=None,
        similarity=None,
    )


def _normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    import re
    # Lowercase, remove extra whitespace, remove punctuation
    normalized = text.lower()
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _calculate_similarity(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings."""
    # Use longest common substring approach
    if len(a) > len(b):
        # Check if a is a substring
        matcher = SequenceMatcher(None, a, b)
        return matcher.ratio()
    else:
        matcher = SequenceMatcher(None, a, b)
        return matcher.ratio()


def _find_best_match(quote: str, content: str) -> str | None:
    """Find the best matching substring in content."""
    words = content.split()
    quote_words = quote.split()
    quote_len = len(quote_words)

    if quote_len == 0:
        return None

    best_match = None
    best_ratio = 0.0

    for i in range(len(words) - quote_len + 1):
        candidate = " ".join(words[i : i + quote_len])
        ratio = SequenceMatcher(None, quote.lower(), candidate.lower()).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = candidate

    return best_match

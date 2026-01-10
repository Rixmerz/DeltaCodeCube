"""Segment comparison tool."""

import sqlite3

from bigcontext_mcp.db.queries import get_segment_by_id, get_segments_by_document
from bigcontext_mcp.search.tfidf import cosine_similarity, get_segment_vector
from bigcontext_mcp.types import (
    BridgeSegment,
    CompareResult,
    SegmentSummary,
    SharedTerm,
    TermScore,
)
from bigcontext_mcp.utils.errors import BigContextError
from bigcontext_mcp.utils.logger import get_logger

logger = get_logger(__name__)


def compare_segments(
    conn: sqlite3.Connection,
    segment_id_a: int,
    segment_id_b: int,
    find_bridges: bool = True,
    max_bridges: int = 3,
) -> CompareResult:
    """
    Compare two segments and find similarities.

    Args:
        conn: Database connection.
        segment_id_a: First segment ID.
        segment_id_b: Second segment ID.
        find_bridges: Whether to find connecting segments.
        max_bridges: Maximum number of bridge segments to return.

    Returns:
        CompareResult with similarity analysis.
    """
    # Get both segments
    segment_a = get_segment_by_id(conn, segment_id_a)
    segment_b = get_segment_by_id(conn, segment_id_b)

    if not segment_a:
        raise BigContextError(f"Segment A with ID {segment_id_a} not found")
    if not segment_b:
        raise BigContextError(f"Segment B with ID {segment_id_b} not found")

    # Get TF-IDF vectors
    vector_a = get_segment_vector(conn, segment_id_a)
    vector_b = get_segment_vector(conn, segment_id_b)

    # Calculate similarity
    similarity_score = cosine_similarity(vector_a, vector_b)

    # Find shared themes (terms that appear in both with significant score)
    shared_themes: list[SharedTerm] = []
    unique_to_a: list[TermScore] = []
    unique_to_b: list[TermScore] = []

    threshold = 0.01

    for term, score_a in vector_a.items():
        score_b = vector_b.get(term)
        if score_b is not None and score_b > threshold and score_a > threshold:
            shared_themes.append(SharedTerm(term=term, score_a=score_a, score_b=score_b))
        elif score_a > threshold:
            unique_to_a.append(TermScore(term=term, score=score_a))

    for term, score_b in vector_b.items():
        if term not in vector_a and score_b > threshold:
            unique_to_b.append(TermScore(term=term, score=score_b))

    # Sort by score
    shared_themes.sort(key=lambda x: x.score_a + x.score_b, reverse=True)
    unique_to_a.sort(key=lambda x: x.score, reverse=True)
    unique_to_b.sort(key=lambda x: x.score, reverse=True)

    # Limit results
    top_shared = shared_themes[:10]
    top_unique_a = unique_to_a[:10]
    top_unique_b = unique_to_b[:10]

    # Find bridge segments if requested and segments are from the same document
    bridge_segments: list[BridgeSegment] | None = None

    if find_bridges and segment_a["document_id"] == segment_b["document_id"]:
        bridge_segments = _find_bridge_segments(
            conn,
            segment_a,
            segment_b,
            vector_a,
            vector_b,
            max_bridges,
        )

    logger.info(
        f"Segments compared: {segment_id_a} vs {segment_id_b}, "
        f"similarity={similarity_score:.3f}, shared_themes={len(top_shared)}"
    )

    return CompareResult(
        segment_a=SegmentSummary(
            id=segment_a["id"],
            title=segment_a.get("title"),
            word_count=segment_a["word_count"],
        ),
        segment_b=SegmentSummary(
            id=segment_b["id"],
            title=segment_b.get("title"),
            word_count=segment_b["word_count"],
        ),
        similarity_score=similarity_score,
        shared_themes=top_shared,
        unique_to_a=top_unique_a,
        unique_to_b=top_unique_b,
        bridge_segments=bridge_segments,
    )


def _find_bridge_segments(
    conn: sqlite3.Connection,
    segment_a: dict,
    segment_b: dict,
    vector_a: dict[str, float],
    vector_b: dict[str, float],
    max_bridges: int,
) -> list[BridgeSegment]:
    """Find segments that connect two endpoints."""
    # Get all segments from the document
    all_segments = get_segments_by_document(conn, segment_a["document_id"])

    # Find segments between A and B
    min_pos = min(segment_a["position"], segment_b["position"])
    max_pos = max(segment_a["position"], segment_b["position"])

    between_segments = [
        s
        for s in all_segments
        if min_pos < s["position"] < max_pos
        and s["id"] != segment_a["id"]
        and s["id"] != segment_b["id"]
    ]

    if not between_segments:
        return []

    # Calculate connection score for each intermediate segment
    scored: list[tuple[dict, float]] = []

    for segment in between_segments:
        vector_bridge = get_segment_vector(conn, segment["id"])

        # Connection score = average similarity to both endpoints
        sim_to_a = cosine_similarity(vector_bridge, vector_a)
        sim_to_b = cosine_similarity(vector_bridge, vector_b)
        connection_score = (sim_to_a + sim_to_b) / 2

        scored.append((segment, connection_score))

    # Sort by connection score and return top bridges
    scored.sort(key=lambda x: x[1], reverse=True)

    return [
        BridgeSegment(
            segment_id=s["id"],
            title=s.get("title"),
            connection_score=score,
        )
        for s, score in scored[:max_bridges]
    ]

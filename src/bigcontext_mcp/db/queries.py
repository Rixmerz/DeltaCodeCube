"""Database query functions."""

import math
import sqlite3
from typing import Any

from bigcontext_mcp.types import (
    Document,
    DocumentFormat,
    DocumentFrequency,
    Segment,
    SegmentInfo,
    SegmentType,
    TermFrequency,
)


# ============================================================================
# Document queries
# ============================================================================


def create_document(
    conn: sqlite3.Connection,
    path: str,
    title: str,
    format: DocumentFormat | str,
    file_hash: str,
) -> int:
    """Create a new document and return its ID."""
    format_str = format.value if isinstance(format, DocumentFormat) else format
    cursor = conn.execute(
        """
        INSERT INTO documents (path, title, format, file_hash)
        VALUES (?, ?, ?, ?)
        """,
        (path, title, format_str, file_hash),
    )
    conn.commit()
    return cursor.lastrowid or 0


def get_document_by_id(conn: sqlite3.Connection, document_id: int) -> dict[str, Any] | None:
    """Get a document by ID."""
    cursor = conn.execute(
        """
        SELECT id, path, title, format, total_words, total_segments,
               file_hash, created_at
        FROM documents WHERE id = ?
        """,
        (document_id,),
    )
    return cursor.fetchone()


def get_document_by_path(conn: sqlite3.Connection, path: str) -> dict[str, Any] | None:
    """Get a document by path."""
    cursor = conn.execute(
        """
        SELECT id, path, title, format, total_words, total_segments,
               file_hash, created_at
        FROM documents WHERE path = ?
        """,
        (path,),
    )
    return cursor.fetchone()


def list_documents(
    conn: sqlite3.Connection, limit: int = 20, offset: int = 0
) -> list[dict[str, Any]]:
    """List all documents."""
    cursor = conn.execute(
        """
        SELECT id, path, title, format, total_words, total_segments,
               file_hash, created_at
        FROM documents
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    )
    return cursor.fetchall()


def update_document_stats(
    conn: sqlite3.Connection,
    document_id: int,
    total_words: int,
    total_segments: int,
) -> None:
    """Update document statistics."""
    conn.execute(
        """
        UPDATE documents
        SET total_words = ?, total_segments = ?, updated_at = datetime('now')
        WHERE id = ?
        """,
        (total_words, total_segments, document_id),
    )
    conn.commit()


def delete_document(conn: sqlite3.Connection, document_id: int) -> bool:
    """Delete a document and return True if deleted."""
    cursor = conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
    conn.commit()
    return cursor.rowcount > 0


def document_exists(conn: sqlite3.Connection, path: str) -> bool:
    """Check if a document exists."""
    cursor = conn.execute("SELECT 1 FROM documents WHERE path = ?", (path,))
    return cursor.fetchone() is not None


# ============================================================================
# Segment queries
# ============================================================================


def create_segment(
    conn: sqlite3.Connection,
    document_id: int,
    parent_segment_id: int | None,
    segment_type: SegmentType | str,
    title: str | None,
    content: str,
    word_count: int,
    position: int,
    start_offset: int | None = None,
    end_offset: int | None = None,
) -> int:
    """Create a new segment and return its ID."""
    type_str = segment_type.value if isinstance(segment_type, SegmentType) else segment_type
    cursor = conn.execute(
        """
        INSERT INTO segments (document_id, parent_segment_id, type, title,
                             content, word_count, position, start_offset, end_offset)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            document_id,
            parent_segment_id,
            type_str,
            title,
            content,
            word_count,
            position,
            start_offset,
            end_offset,
        ),
    )
    conn.commit()
    return cursor.lastrowid or 0


def create_segments_batch(
    conn: sqlite3.Connection,
    segments: list[dict[str, Any]],
) -> list[int]:
    """Create multiple segments in a transaction."""
    ids: list[int] = []
    for seg in segments:
        type_str = (
            seg["type"].value if isinstance(seg["type"], SegmentType) else seg["type"]
        )
        cursor = conn.execute(
            """
            INSERT INTO segments (document_id, parent_segment_id, type, title,
                                 content, word_count, position, start_offset, end_offset)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                seg["document_id"],
                seg.get("parent_segment_id"),
                type_str,
                seg.get("title"),
                seg["content"],
                seg["word_count"],
                seg["position"],
                seg.get("start_offset"),
                seg.get("end_offset"),
            ),
        )
        ids.append(cursor.lastrowid or 0)
    conn.commit()
    return ids


def get_segment_by_id(conn: sqlite3.Connection, segment_id: int) -> dict[str, Any] | None:
    """Get a segment by ID."""
    cursor = conn.execute(
        """
        SELECT id, document_id, parent_segment_id, type, title,
               content, word_count, position
        FROM segments WHERE id = ?
        """,
        (segment_id,),
    )
    return cursor.fetchone()


def get_segments_by_document(
    conn: sqlite3.Connection, document_id: int
) -> list[dict[str, Any]]:
    """Get all segments for a document."""
    cursor = conn.execute(
        """
        SELECT id, document_id, parent_segment_id, type, title,
               content, word_count, position
        FROM segments WHERE document_id = ?
        ORDER BY position
        """,
        (document_id,),
    )
    return cursor.fetchall()


def get_document_structure(
    conn: sqlite3.Connection, document_id: int
) -> list[dict[str, Any]]:
    """Get document structure (chapters and sections only)."""
    cursor = conn.execute(
        """
        SELECT id as segment_id, type, title, word_count, position
        FROM segments
        WHERE document_id = ? AND type IN ('chapter', 'section')
        ORDER BY position
        """,
        (document_id,),
    )
    return cursor.fetchall()


def get_chunks_by_parent(
    conn: sqlite3.Connection, parent_id: int
) -> list[dict[str, Any]]:
    """Get chunks by parent segment ID."""
    cursor = conn.execute(
        """
        SELECT id, document_id, parent_segment_id, type, title,
               content, word_count, position
        FROM segments
        WHERE parent_segment_id = ? AND type = 'chunk'
        ORDER BY position
        """,
        (parent_id,),
    )
    return cursor.fetchall()


def delete_segments_by_document(conn: sqlite3.Connection, document_id: int) -> None:
    """Delete all segments for a document."""
    conn.execute("DELETE FROM segments WHERE document_id = ?", (document_id,))
    conn.commit()


def count_segments(conn: sqlite3.Connection, document_id: int | None = None) -> int:
    """Count segments, optionally for a specific document."""
    if document_id:
        cursor = conn.execute(
            "SELECT COUNT(*) as count FROM segments WHERE document_id = ?",
            (document_id,),
        )
    else:
        cursor = conn.execute("SELECT COUNT(*) as count FROM segments")
    result = cursor.fetchone()
    return result["count"] if result else 0


def get_adjacent_segments(
    conn: sqlite3.Connection,
    base_segment_id: int,
    max_distance: int = 1,
) -> list[dict[str, Any]]:
    """Get segments adjacent to a base segment."""
    # First get the base segment's position and document_id
    base = get_segment_by_id(conn, base_segment_id)
    if not base:
        return []

    cursor = conn.execute(
        """
        SELECT id, document_id, parent_segment_id, type, title,
               content, word_count, position
        FROM segments
        WHERE document_id = ?
          AND position BETWEEN ? AND ?
          AND id != ?
        ORDER BY position
        """,
        (
            base["document_id"],
            base["position"] - max_distance,
            base["position"] + max_distance,
            base_segment_id,
        ),
    )
    return cursor.fetchall()


# ============================================================================
# Term frequency queries
# ============================================================================


def insert_term_frequencies(
    conn: sqlite3.Connection,
    terms: list[dict[str, Any]],
) -> None:
    """Insert term frequencies for a segment."""
    for term in terms:
        conn.execute(
            """
            INSERT OR REPLACE INTO term_frequencies (segment_id, term, count, tf)
            VALUES (?, ?, ?, ?)
            """,
            (term["segment_id"], term["term"], term["count"], term["tf"]),
        )
    conn.commit()


def get_term_frequencies_for_segment(
    conn: sqlite3.Connection, segment_id: int
) -> list[dict[str, Any]]:
    """Get term frequencies for a segment."""
    cursor = conn.execute(
        """
        SELECT segment_id, term, count, tf
        FROM term_frequencies WHERE segment_id = ?
        ORDER BY tf DESC
        """,
        (segment_id,),
    )
    return cursor.fetchall()


def get_top_terms_for_segment(
    conn: sqlite3.Connection, segment_id: int, limit: int = 10
) -> list[dict[str, Any]]:
    """Get top terms for a segment by TF score."""
    cursor = conn.execute(
        """
        SELECT segment_id, term, count, tf
        FROM term_frequencies WHERE segment_id = ?
        ORDER BY tf DESC LIMIT ?
        """,
        (segment_id, limit),
    )
    return cursor.fetchall()


def update_document_frequencies(conn: sqlite3.Connection) -> None:
    """Recalculate document frequencies and IDF values."""
    # Delete and recalculate DF
    conn.execute("DELETE FROM document_frequencies")
    conn.execute(
        """
        INSERT INTO document_frequencies (term, df, idf, updated_at)
        SELECT
            term,
            COUNT(DISTINCT segment_id) as df,
            0.0 as idf,
            datetime('now')
        FROM term_frequencies
        GROUP BY term
        """
    )

    # Get total segments
    cursor = conn.execute("SELECT COUNT(*) as count FROM segments")
    result = cursor.fetchone()
    total_segments = result["count"] if result else 0

    if total_segments > 0:
        # Calculate IDF: log(N / (1 + df))
        conn.execute(
            """
            UPDATE document_frequencies
            SET idf = ?
            """,
            (math.log(total_segments),),
        )
        # Actually we need to do this per-row, using a workaround
        cursor = conn.execute("SELECT term, df FROM document_frequencies")
        for row in cursor.fetchall():
            idf = math.log(total_segments / (1 + row["df"]))
            conn.execute(
                "UPDATE document_frequencies SET idf = ? WHERE term = ?",
                (idf, row["term"]),
            )

    conn.commit()


def get_document_frequency(
    conn: sqlite3.Connection, term: str
) -> dict[str, Any] | None:
    """Get document frequency for a term."""
    cursor = conn.execute(
        "SELECT term, df, idf FROM document_frequencies WHERE term = ?",
        (term,),
    )
    return cursor.fetchone()


def get_document_frequencies(
    conn: sqlite3.Connection, terms: list[str]
) -> dict[str, dict[str, Any]]:
    """Get document frequencies for multiple terms."""
    if not terms:
        return {}

    placeholders = ",".join("?" * len(terms))
    cursor = conn.execute(
        f"SELECT term, df, idf FROM document_frequencies WHERE term IN ({placeholders})",
        terms,
    )
    return {row["term"]: row for row in cursor.fetchall()}


def search_segments_by_terms(
    conn: sqlite3.Connection,
    terms: list[str],
    document_id: int | None = None,
    segment_id: int | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search segments by terms using TF-IDF scoring."""
    if not terms:
        return []

    placeholders = ",".join("?" * len(terms))
    params: list[Any] = list(terms)

    where_clause = f"tf.term IN ({placeholders})"

    if document_id:
        where_clause += " AND s.document_id = ?"
        params.append(document_id)

    if segment_id:
        where_clause += " AND s.id = ?"
        params.append(segment_id)

    params.append(limit)

    cursor = conn.execute(
        f"""
        SELECT
            s.id as segment_id,
            s.document_id,
            SUM(tf.tf * COALESCE(df.idf, 1.0)) as score,
            GROUP_CONCAT(DISTINCT tf.term) as matched_terms_str
        FROM segments s
        JOIN term_frequencies tf ON s.id = tf.segment_id
        LEFT JOIN document_frequencies df ON tf.term = df.term
        WHERE {where_clause}
        GROUP BY s.id
        ORDER BY score DESC
        LIMIT ?
        """,
        params,
    )

    results = []
    for row in cursor.fetchall():
        results.append({
            "segment_id": row["segment_id"],
            "document_id": row["document_id"],
            "score": row["score"],
            "matched_terms": (
                row["matched_terms_str"].split(",")
                if row["matched_terms_str"]
                else []
            ),
        })
    return results


def delete_term_frequencies_for_document(
    conn: sqlite3.Connection, document_id: int
) -> None:
    """Delete term frequencies for all segments of a document."""
    conn.execute(
        """
        DELETE FROM term_frequencies
        WHERE segment_id IN (SELECT id FROM segments WHERE document_id = ?)
        """,
        (document_id,),
    )
    conn.commit()


# ============================================================================
# Vocabulary queries
# ============================================================================


def build_document_vocabulary(conn: sqlite3.Connection, document_id: int) -> int:
    """Build vocabulary for a document from its segments. Returns vocabulary size."""
    # Delete existing vocabulary
    conn.execute(
        "DELETE FROM document_vocabulary WHERE document_id = ?", (document_id,)
    )

    # Insert all unique tokens with frequencies
    conn.execute(
        """
        INSERT INTO document_vocabulary (document_id, token, frequency)
        SELECT ?, term, SUM(count)
        FROM term_frequencies tf
        JOIN segments s ON tf.segment_id = s.id
        WHERE s.document_id = ?
        GROUP BY term
        """,
        (document_id, document_id),
    )

    # Get vocabulary size
    cursor = conn.execute(
        "SELECT COUNT(*) as count FROM document_vocabulary WHERE document_id = ?",
        (document_id,),
    )
    result = cursor.fetchone()
    vocab_size = result["count"] if result else 0

    # Update metadata
    conn.execute(
        """
        INSERT OR REPLACE INTO document_metadata
            (document_id, vocabulary_size, vocabulary_built_at)
        VALUES (?, ?, datetime('now'))
        """,
        (document_id, vocab_size),
    )

    conn.commit()
    return vocab_size


def get_document_vocabulary(
    conn: sqlite3.Connection, document_id: int
) -> set[str]:
    """Get the vocabulary set for a document."""
    cursor = conn.execute(
        "SELECT token FROM document_vocabulary WHERE document_id = ?",
        (document_id,),
    )
    return {row["token"] for row in cursor.fetchall()}


def validate_tokens_in_vocabulary(
    conn: sqlite3.Connection, document_id: int, tokens: list[str]
) -> tuple[set[str], set[str]]:
    """Validate tokens against document vocabulary. Returns (valid, invalid) sets."""
    vocab = get_document_vocabulary(conn, document_id)
    token_set = set(tokens)
    valid = token_set & vocab
    invalid = token_set - vocab
    return valid, invalid

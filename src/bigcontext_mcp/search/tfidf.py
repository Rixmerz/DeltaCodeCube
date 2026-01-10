"""TF-IDF implementation for document search."""

import math
import sqlite3
from dataclasses import dataclass
from typing import Any

from bigcontext_mcp.db.queries import (
    get_document_by_id,
    get_document_frequencies,
    get_segment_by_id,
    insert_term_frequencies,
    search_segments_by_terms,
    update_document_frequencies,
)
from bigcontext_mcp.search.tokenizer import TokenizeOptions, count_term_frequencies, tokenize
from bigcontext_mcp.types import SearchResult, SearchResultItem, SegmentType, TermScore


@dataclass
class TfIdfOptions:
    """Options for TF-IDF indexing."""

    min_term_frequency: int = 1
    max_terms: int = 1000


def index_segment(
    conn: sqlite3.Connection,
    segment_id: int,
    content: str,
    options: TfIdfOptions | None = None,
) -> None:
    """Index a segment's content for TF-IDF search."""
    opts = options or TfIdfOptions()

    # Tokenize and count frequencies
    frequencies = count_term_frequencies(content)
    total_terms = sum(frequencies.values())

    if total_terms == 0:
        return

    # Calculate TF for each term
    term_frequencies: list[dict[str, Any]] = []

    for term, count in frequencies.items():
        if count >= opts.min_term_frequency:
            tf = count / total_terms
            term_frequencies.append({
                "segment_id": segment_id,
                "term": term,
                "count": count,
                "tf": tf,
            })

    # Limit number of terms if needed
    sorted_terms = sorted(term_frequencies, key=lambda x: x["count"], reverse=True)
    sorted_terms = sorted_terms[: opts.max_terms]

    # Insert into database
    if sorted_terms:
        insert_term_frequencies(conn, sorted_terms)


def rebuild_idf(conn: sqlite3.Connection) -> None:
    """Rebuild the IDF values after indexing changes."""
    update_document_frequencies(conn)


def search(
    conn: sqlite3.Connection,
    query: str,
    document_id: int | None = None,
    segment_id: int | None = None,
    limit: int = 10,
    context_words: int = 50,
) -> SearchResult:
    """Search for segments matching the query."""
    # Tokenize query
    query_terms = tokenize(query, TokenizeOptions(remove_stop_words=True))

    if not query_terms:
        return SearchResult(results=[], total_matches=0, query_terms=[])

    # Search for matching segments
    matches = search_segments_by_terms(
        conn,
        query_terms,
        document_id=document_id,
        segment_id=segment_id,
        limit=limit,
    )

    # Build results with snippets
    results: list[SearchResultItem] = []

    for match in matches:
        segment = get_segment_by_id(conn, match["segment_id"])
        if not segment:
            continue

        document = get_document_by_id(conn, match["document_id"])
        if not document:
            continue

        # Generate snippet around matched terms
        snippet = generate_snippet(
            segment["content"], match["matched_terms"], context_words
        )

        results.append(
            SearchResultItem(
                segment_id=match["segment_id"],
                document_id=match["document_id"],
                document_title=document["title"],
                segment_title=segment.get("title"),
                segment_type=SegmentType(segment["type"]),
                score=match["score"],
                snippet=snippet,
                matched_terms=match["matched_terms"],
                position=segment["position"],
            )
        )

    return SearchResult(
        results=results,
        total_matches=len(results),
        query_terms=query_terms,
    )


def generate_snippet(
    content: str, matched_terms: list[str], context_words: int
) -> str:
    """Generate a snippet around the first occurrence of any matched term."""
    words = content.split()
    lower_content = content.lower()

    # Find first occurrence of any matched term
    first_match_index = -1
    matched_term = ""

    for term in matched_terms:
        term_lower = term.lower()
        index = lower_content.find(term_lower)
        if index != -1 and (first_match_index == -1 or index < first_match_index):
            first_match_index = index
            matched_term = term

    if first_match_index == -1:
        # No match found, return beginning of content
        snippet_words = words[: context_words * 2]
        return " ".join(snippet_words) + ("..." if len(words) > context_words * 2 else "")

    # Find word index at the match position
    char_count = 0
    match_word_index = 0
    for i, word in enumerate(words):
        if char_count >= first_match_index:
            match_word_index = i
            break
        char_count += len(word) + 1

    # Extract context around the match
    start_index = max(0, match_word_index - context_words)
    end_index = min(len(words), match_word_index + context_words)

    snippet = ""
    if start_index > 0:
        snippet += "..."
    snippet += " ".join(words[start_index:end_index])
    if end_index < len(words):
        snippet += "..."

    return snippet


def get_segment_vector(
    conn: sqlite3.Connection, segment_id: int
) -> dict[str, float]:
    """Get TF-IDF vector for a segment."""
    vector: dict[str, float] = {}

    cursor = conn.execute(
        "SELECT term, tf FROM term_frequencies WHERE segment_id = ?",
        (segment_id,),
    )
    term_freqs = cursor.fetchall()

    terms = [t["term"] for t in term_freqs]
    df_map = get_document_frequencies(conn, terms)

    for row in term_freqs:
        term = row["term"]
        tf = row["tf"]
        df = df_map.get(term)
        idf = df["idf"] if df else 1.0
        vector[term] = tf * idf

    return vector


def cosine_similarity(
    vector_a: dict[str, float], vector_b: dict[str, float]
) -> float:
    """Calculate cosine similarity between two TF-IDF vectors."""
    all_terms = set(vector_a.keys()) | set(vector_b.keys())

    dot_product = 0.0
    magnitude_a = 0.0
    magnitude_b = 0.0

    for term in all_terms:
        a = vector_a.get(term, 0.0)
        b = vector_b.get(term, 0.0)

        dot_product += a * b
        magnitude_a += a * a
        magnitude_b += b * b

    magnitude_a = math.sqrt(magnitude_a)
    magnitude_b = math.sqrt(magnitude_b)

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


def get_top_terms_by_tfidf(
    conn: sqlite3.Connection, segment_id: int, limit: int = 10
) -> list[TermScore]:
    """Get top terms for a segment by TF-IDF score."""
    vector = get_segment_vector(conn, segment_id)

    sorted_terms = sorted(vector.items(), key=lambda x: x[1], reverse=True)
    return [TermScore(term=term, score=score) for term, score in sorted_terms[:limit]]

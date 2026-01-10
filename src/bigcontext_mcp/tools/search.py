"""Search tool."""

import sqlite3

from bigcontext_mcp.search.tfidf import search
from bigcontext_mcp.types import SearchResult
from bigcontext_mcp.utils.logger import get_logger

logger = get_logger(__name__)


def search_segments(
    conn: sqlite3.Connection,
    query: str,
    document_id: int | None = None,
    segment_id: int | None = None,
    limit: int = 5,
    context_words: int = 50,
) -> SearchResult:
    """
    Search for segments matching a query.

    Args:
        conn: Database connection.
        query: Search query string.
        document_id: Optional document ID to limit search.
        segment_id: Optional segment ID to search within.
        limit: Maximum number of results.
        context_words: Number of context words in snippets.

    Returns:
        SearchResult with matching segments.
    """
    logger.debug(
        f"Searching: query='{query}', document_id={document_id}, "
        f"segment_id={segment_id}, limit={limit}"
    )

    result = search(
        conn,
        query,
        document_id=document_id,
        segment_id=segment_id,
        limit=limit,
        context_words=context_words,
    )

    logger.info(
        f"Search completed: query='{query}', "
        f"matches={result.total_matches}, terms={result.query_terms}"
    )

    return result

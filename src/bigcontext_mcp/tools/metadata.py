"""Metadata and document listing tools."""

import sqlite3
from dataclasses import dataclass
from typing import Any

from bigcontext_mcp.db.queries import (
    get_document_by_id,
    get_document_structure,
    get_segment_by_id,
    list_documents,
)
from bigcontext_mcp.search.tfidf import get_top_terms_by_tfidf
from bigcontext_mcp.types import (
    DocumentFormat,
    DocumentInfo,
    MetadataResult,
    SegmentMetadata,
    SegmentType,
    StructureItem,
)
from bigcontext_mcp.utils.errors import BigContextError
from bigcontext_mcp.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ListDocumentsResult:
    """Result of listing documents."""

    documents: list[dict[str, Any]]
    total: int


def get_metadata(
    conn: sqlite3.Connection,
    document_id: int | None = None,
    segment_id: int | None = None,
    top_terms: int = 10,
    include_structure: bool = True,
) -> MetadataResult:
    """
    Get metadata for a document or segment.

    Args:
        conn: Database connection.
        document_id: Document ID to get metadata for.
        segment_id: Segment ID to get metadata for.
        top_terms: Number of top terms to return.
        include_structure: Whether to include document structure.

    Returns:
        MetadataResult with document and/or segment info.
    """
    if not document_id and not segment_id:
        raise BigContextError("Either document_id or segment_id must be provided")

    result = MetadataResult()

    # Get document info if document_id provided
    if document_id:
        doc = get_document_by_id(conn, document_id)
        if not doc:
            raise BigContextError(f"Document with ID {document_id} not found")

        result.document = DocumentInfo(
            id=doc["id"],
            path=doc["path"],
            title=doc["title"],
            format=DocumentFormat(doc["format"]),
            total_words=doc["total_words"],
            total_segments=doc["total_segments"],
            created_at=doc["created_at"],
        )

        # Get document structure if requested
        if include_structure:
            segments = get_document_structure(conn, document_id)
            result.structure = [
                StructureItem(
                    segment_id=seg["segment_id"],
                    type=SegmentType(seg["type"]),
                    title=seg.get("title"),
                    word_count=seg["word_count"],
                    depth=0 if seg["type"] == "chapter" else 1,
                )
                for seg in segments
            ]

    # Get segment info if segment_id provided
    if segment_id:
        segment = get_segment_by_id(conn, segment_id)
        if not segment:
            raise BigContextError(f"Segment with ID {segment_id} not found")

        result.segment = SegmentMetadata(
            id=segment["id"],
            type=SegmentType(segment["type"]),
            title=segment.get("title"),
            word_count=segment["word_count"],
            position=segment["position"],
        )

        # Get top terms for segment
        result.top_terms = get_top_terms_by_tfidf(conn, segment_id, top_terms)

        # If document not already loaded, get it for context
        if not result.document:
            doc = get_document_by_id(conn, segment["document_id"])
            if doc:
                result.document = DocumentInfo(
                    id=doc["id"],
                    path=doc["path"],
                    title=doc["title"],
                    format=DocumentFormat(doc["format"]),
                    total_words=doc["total_words"],
                    total_segments=doc["total_segments"],
                    created_at=doc["created_at"],
                )

    logger.debug(f"Metadata retrieved: document_id={document_id}, segment_id={segment_id}")

    return result


def get_documents_list(
    conn: sqlite3.Connection,
    limit: int = 20,
    offset: int = 0,
) -> ListDocumentsResult:
    """
    List all documents.

    Args:
        conn: Database connection.
        limit: Maximum number of documents to return.
        offset: Number of documents to skip.

    Returns:
        ListDocumentsResult with documents and total count.
    """
    documents = list_documents(conn, limit, offset)

    # Get total count
    cursor = conn.execute("SELECT COUNT(*) as count FROM documents")
    result = cursor.fetchone()
    total = result["count"] if result else 0

    logger.debug(f"Documents listed: count={len(documents)}, total={total}")

    return ListDocumentsResult(
        documents=[
            {
                "id": d["id"],
                "path": d["path"],
                "title": d["title"],
                "format": d["format"],
                "total_words": d["total_words"],
                "total_segments": d["total_segments"],
                "created_at": d["created_at"],
            }
            for d in documents
        ],
        total=total,
    )

"""Document ingestion tool."""

import hashlib
import sqlite3
import time
from pathlib import Path
from typing import Any

from bigcontext_mcp.db.queries import (
    create_document,
    create_segments_batch,
    delete_document,
    delete_segments_by_document,
    delete_term_frequencies_for_document,
    get_document_by_path,
    update_document_stats,
)
from bigcontext_mcp.parsers import detect_format, parse_document
from bigcontext_mcp.search.tfidf import index_segment, rebuild_idf
from bigcontext_mcp.segmentation.chunker import count_words
from bigcontext_mcp.segmentation.segmenter import SegmentationOptions, segment_document
from bigcontext_mcp.types import DocumentFormat, IngestResult, SegmentInfo
from bigcontext_mcp.utils.errors import BigContextError
from bigcontext_mcp.utils.logger import get_logger

logger = get_logger(__name__)


def ingest_document(
    conn: sqlite3.Connection,
    path: str,
    title: str | None = None,
    chunk_size: int = 2000,
    overlap: int = 100,
    force: bool = False,
) -> IngestResult:
    """
    Ingest a document into the database.

    Args:
        conn: Database connection.
        path: Path to the document file.
        title: Optional title override.
        chunk_size: Target chunk size in words.
        overlap: Number of words to overlap between chunks.
        force: Force re-indexing even if document already exists.

    Returns:
        IngestResult with document metadata.
    """
    start_time = time.time()

    # Resolve path
    file_path = Path(path).resolve()

    if not file_path.exists():
        raise BigContextError(f"File not found: {file_path}")

    # Detect format
    doc_format = detect_format(file_path)
    if not doc_format:
        raise BigContextError(f"Unsupported file format: {file_path.suffix}")

    # Calculate file hash
    file_content = file_path.read_bytes()
    file_hash = hashlib.md5(file_content).hexdigest()

    # Check if document already exists
    existing_doc = get_document_by_path(conn, str(file_path))
    if existing_doc:
        if not force and existing_doc.get("file_hash") == file_hash:
            logger.info(f"Document already indexed with same hash: {file_path}")
            return IngestResult(
                success=True,
                document_id=existing_doc["id"],
                title=existing_doc["title"],
                format=DocumentFormat(existing_doc["format"]),
                total_segments=existing_doc["total_segments"],
                total_words=existing_doc["total_words"],
                structure=[],
                processing_time_ms=(time.time() - start_time) * 1000,
            )

        # Delete existing document data for re-indexing
        logger.info(f"Re-indexing existing document: {file_path}")
        delete_term_frequencies_for_document(conn, existing_doc["id"])
        delete_segments_by_document(conn, existing_doc["id"])
        delete_document(conn, existing_doc["id"])

    # Parse document
    logger.info(f"Parsing document: {file_path} (format: {doc_format})")
    content, metadata = parse_document(file_path, doc_format)

    # Extract title from params, metadata, or filename
    doc_title = title or metadata.get("title") or file_path.stem

    # Create document record
    document_id = create_document(
        conn,
        path=str(file_path),
        title=doc_title,
        format=doc_format,
        file_hash=file_hash,
    )

    # Segment the document
    logger.info(f"Segmenting document (chunk_size={chunk_size})")
    segmentation_result = segment_document(
        content,
        SegmentationOptions(
            chunk_size=chunk_size,
            overlap=overlap,
        ),
    )

    # Create segment records
    segment_params = [
        {
            "document_id": document_id,
            "parent_segment_id": None,
            "type": seg.type.value,
            "title": seg.title,
            "content": seg.content,
            "word_count": count_words(seg.content),
            "position": index,
            "start_offset": seg.start_offset,
            "end_offset": seg.end_offset,
        }
        for index, seg in enumerate(segmentation_result.segments)
    ]

    segment_ids = create_segments_batch(conn, segment_params)

    # Index each segment for search
    logger.info(f"Indexing {len(segment_ids)} segments for search")
    for i, seg_id in enumerate(segment_ids):
        index_segment(conn, seg_id, segmentation_result.segments[i].content)

    # Rebuild IDF after indexing
    rebuild_idf(conn)

    # Update document stats
    total_words = sum(s["word_count"] for s in segment_params)
    update_document_stats(conn, document_id, total_words, len(segment_ids))

    # Build structure info
    structure = [
        SegmentInfo(
            segment_id=segment_ids[i],
            type=segmentation_result.segments[i].type,
            title=segmentation_result.segments[i].title,
            word_count=segment_params[i]["word_count"],
            position=i,
        )
        for i in range(len(segment_ids))
    ]

    processing_time = (time.time() - start_time) * 1000

    logger.info(
        f"Document ingested: id={document_id}, "
        f"segments={len(segment_ids)}, words={total_words}, "
        f"pattern={segmentation_result.pattern_used}"
    )

    return IngestResult(
        success=True,
        document_id=document_id,
        title=doc_title,
        format=doc_format,
        total_segments=len(segment_ids),
        total_words=total_words,
        structure=structure,
        processing_time_ms=processing_time,
    )

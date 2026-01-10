"""Database module for BigContext MCP."""

from bigcontext_mcp.db.database import close_database, get_database, init_database
from bigcontext_mcp.db.queries import (
    create_document,
    create_segment,
    delete_document,
    get_document_by_id,
    get_document_by_path,
    get_segment_by_id,
    get_segments_by_document,
    list_documents,
    update_document_stats,
)

__all__ = [
    "init_database",
    "get_database",
    "close_database",
    "create_document",
    "get_document_by_id",
    "get_document_by_path",
    "delete_document",
    "list_documents",
    "update_document_stats",
    "create_segment",
    "get_segment_by_id",
    "get_segments_by_document",
]

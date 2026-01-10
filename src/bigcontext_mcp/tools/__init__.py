"""MCP Tools for BigContext."""

from bigcontext_mcp.tools.compare import compare_segments
from bigcontext_mcp.tools.ingest import ingest_document
from bigcontext_mcp.tools.metadata import get_documents_list, get_metadata
from bigcontext_mcp.tools.search import search_segments

__all__ = [
    "ingest_document",
    "search_segments",
    "get_metadata",
    "get_documents_list",
    "compare_segments",
]

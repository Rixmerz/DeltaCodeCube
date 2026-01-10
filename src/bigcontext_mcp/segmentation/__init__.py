"""Document segmentation module."""

from bigcontext_mcp.segmentation.chunker import Chunk, ChunkOptions, chunk_text, count_words
from bigcontext_mcp.segmentation.patterns import (
    CHAPTER_PATTERNS,
    ChapterPattern,
    DetectedPattern,
    detect_patterns,
    filter_best_patterns,
)

__all__ = [
    "CHAPTER_PATTERNS",
    "ChapterPattern",
    "DetectedPattern",
    "detect_patterns",
    "filter_best_patterns",
    "Chunk",
    "ChunkOptions",
    "chunk_text",
    "count_words",
]

"""Chapter and section detection patterns."""

import re
from dataclasses import dataclass
from typing import Callable

from bigcontext_mcp.types import SegmentType


@dataclass
class ChapterPattern:
    """Pattern for detecting chapters and sections."""

    name: str
    regex: re.Pattern[str]
    confidence: float
    segment_type: SegmentType
    extract_title: Callable[[re.Match[str]], str | None]


@dataclass
class DetectedPattern:
    """A detected pattern in the document."""

    pattern: ChapterPattern
    match: re.Match[str]
    start_index: int
    end_index: int
    title: str | None


# Pattern definitions
CHAPTER_PATTERNS: list[ChapterPattern] = [
    # "Chapter 1: Title" or "CHAPTER I"
    ChapterPattern(
        name="numbered_chapter",
        regex=re.compile(
            r"^(?:Chapter|CHAPTER|Capitulo|CAPITULO)\s+(\d+|[IVXLCDM]+)"
            r"(?:\s*[:\.\-—]\s*(.+))?$",
            re.MULTILINE,
        ),
        confidence=0.95,
        segment_type=SegmentType.CHAPTER,
        extract_title=lambda m: (m.group(2) or "").strip() or f"Chapter {m.group(1)}",
    ),
    # "Part 1: Title" or "PART II"
    ChapterPattern(
        name="part",
        regex=re.compile(
            r"^(?:Part|PART|Parte|PARTE)\s+(\d+|[IVXLCDM]+)"
            r"(?:\s*[:\.\-—]\s*(.+))?$",
            re.MULTILINE,
        ),
        confidence=0.9,
        segment_type=SegmentType.CHAPTER,
        extract_title=lambda m: (m.group(2) or "").strip() or f"Part {m.group(1)}",
    ),
    # "Book 1" or "BOOK I"
    ChapterPattern(
        name="book",
        regex=re.compile(
            r"^(?:Book|BOOK|Libro|LIBRO)\s+(\d+|[IVXLCDM]+)"
            r"(?:\s*[:\.\-—]\s*(.+))?$",
            re.MULTILINE,
        ),
        confidence=0.9,
        segment_type=SegmentType.CHAPTER,
        extract_title=lambda m: (m.group(2) or "").strip() or f"Book {m.group(1)}",
    ),
    # Markdown H1: "# Title"
    ChapterPattern(
        name="markdown_h1",
        regex=re.compile(r"^#\s+(.+)$", re.MULTILINE),
        confidence=0.85,
        segment_type=SegmentType.CHAPTER,
        extract_title=lambda m: m.group(1).strip(),
    ),
    # Markdown H2: "## Title"
    ChapterPattern(
        name="markdown_h2",
        regex=re.compile(r"^##\s+(.+)$", re.MULTILINE),
        confidence=0.7,
        segment_type=SegmentType.SECTION,
        extract_title=lambda m: m.group(1).strip(),
    ),
    # Markdown H3: "### Title"
    ChapterPattern(
        name="markdown_h3",
        regex=re.compile(r"^###\s+(.+)$", re.MULTILINE),
        confidence=0.6,
        segment_type=SegmentType.SECTION,
        extract_title=lambda m: m.group(1).strip(),
    ),
    # Numbered section: "1.2.3 Title"
    ChapterPattern(
        name="numbered_section",
        regex=re.compile(r"^(\d+(?:\.\d+)+)\s+(.+)$", re.MULTILINE),
        confidence=0.6,
        segment_type=SegmentType.SECTION,
        extract_title=lambda m: f"{m.group(1)} {m.group(2)}",
    ),
    # Simple numbered: "1. Title" at the start of a paragraph
    ChapterPattern(
        name="simple_numbered",
        regex=re.compile(r"^(\d+)\.\s+([A-Z][^\n]{5,50})$", re.MULTILINE),
        confidence=0.5,
        segment_type=SegmentType.SECTION,
        extract_title=lambda m: f"{m.group(1)}. {m.group(2)}",
    ),
    # ALL CAPS TITLE (at least 3 words, all caps)
    ChapterPattern(
        name="all_caps_title",
        regex=re.compile(r"^([A-Z][A-Z\s]{10,60})$", re.MULTILINE),
        confidence=0.4,
        segment_type=SegmentType.CHAPTER,
        extract_title=lambda m: m.group(1).strip(),
    ),
    # Drama/Play: "Act I", "Scene 2"
    ChapterPattern(
        name="dramatic",
        regex=re.compile(
            r"^(?:Act|ACT|Scene|SCENE|Acto|ACTO|Escena|ESCENA)\s+(\d+|[IVXLCDM]+)"
            r"(?:\s*[:\.\-—]\s*(.+))?$",
            re.MULTILINE,
        ),
        confidence=0.9,
        segment_type=SegmentType.CHAPTER,
        extract_title=lambda m: (m.group(2) or "").strip() or m.group(0),
    ),
    # Bible-style: "Genesis 1" or "Psalm 23"
    ChapterPattern(
        name="bible_book",
        regex=re.compile(r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(\d+)$", re.MULTILINE),
        confidence=0.7,
        segment_type=SegmentType.CHAPTER,
        extract_title=lambda m: f"{m.group(1)} {m.group(2)}",
    ),
]


def detect_patterns(content: str) -> list[DetectedPattern]:
    """Detect all chapter/section patterns in content."""
    detected: list[DetectedPattern] = []
    lines = content.split("\n")
    char_offset = 0

    for line in lines:
        trimmed_line = line.strip()

        if not trimmed_line:
            char_offset += len(line) + 1
            continue

        for pattern in CHAPTER_PATTERNS:
            match = pattern.regex.match(trimmed_line)
            if match:
                detected.append(
                    DetectedPattern(
                        pattern=pattern,
                        match=match,
                        start_index=char_offset,
                        end_index=char_offset + len(line),
                        title=pattern.extract_title(match),
                    )
                )
                break  # Only match one pattern per line

        char_offset += len(line) + 1

    # Sort by confidence (descending) then by position
    return sorted(
        detected,
        key=lambda d: (-d.pattern.confidence, d.start_index),
    )


def filter_best_patterns(
    detected: list[DetectedPattern],
    min_confidence: float = 0.5,
) -> list[DetectedPattern]:
    """Filter to keep only the best pattern type."""
    if not detected:
        return []

    # Group by pattern type
    by_type: dict[str, list[DetectedPattern]] = {}
    for d in detected:
        pattern_name = d.pattern.name
        if pattern_name not in by_type:
            by_type[pattern_name] = []
        by_type[pattern_name].append(d)

    # Find the most common high-confidence pattern
    best_type: str | None = None
    best_count = 0
    best_confidence = 0.0

    for pattern_name, items in by_type.items():
        confidence = items[0].pattern.confidence
        if confidence >= min_confidence:
            if len(items) > best_count or (
                len(items) == best_count and confidence > best_confidence
            ):
                best_type = pattern_name
                best_count = len(items)
                best_confidence = confidence

    if best_type is None:
        return []

    # Return all detections of the best type, sorted by position
    return sorted(by_type[best_type], key=lambda d: d.start_index)

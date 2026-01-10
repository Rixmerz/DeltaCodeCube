"""Document segmentation orchestrator."""

from dataclasses import dataclass

from bigcontext_mcp.segmentation.chunker import ChunkOptions, chunk_text, count_words
from bigcontext_mcp.segmentation.patterns import detect_patterns, filter_best_patterns
from bigcontext_mcp.types import DetectedSegment, SegmentType


@dataclass
class SegmentationOptions:
    """Options for document segmentation."""

    chunk_size: int = 2000
    overlap: int = 100
    min_chapter_size: int = 500
    fallback_to_chunks: bool = True


@dataclass
class SegmentationResult:
    """Result of document segmentation."""

    segments: list[DetectedSegment]
    total_words: int
    pattern_used: str | None


def segment_document(
    content: str,
    options: SegmentationOptions | None = None,
) -> SegmentationResult:
    """Segment a document into chapters, sections, and chunks."""
    opts = options or SegmentationOptions()
    total_words = count_words(content)

    # Step 1: Try to detect chapter/section patterns
    all_patterns = detect_patterns(content)
    best_patterns = filter_best_patterns(all_patterns)

    # If we found good patterns, segment by them
    if best_patterns:
        segments = _segment_by_patterns(content, best_patterns, opts)
        if segments:
            return SegmentationResult(
                segments=segments,
                total_words=total_words,
                pattern_used=best_patterns[0].pattern.name,
            )

    # Step 2: Fallback to fixed-size chunking
    if opts.fallback_to_chunks:
        chunks = chunk_text(
            content,
            ChunkOptions(
                chunk_size=opts.chunk_size,
                overlap=opts.overlap,
                respect_paragraphs=True,
            ),
        )

        segments = [
            DetectedSegment(
                type=SegmentType.CHUNK,
                title=f"Chunk {i + 1}",
                content=chunk.content,
                start_offset=chunk.start_offset,
                end_offset=chunk.end_offset,
            )
            for i, chunk in enumerate(chunks)
        ]

        return SegmentationResult(
            segments=segments,
            total_words=total_words,
            pattern_used="fallback_chunks",
        )

    # No segmentation possible
    return SegmentationResult(
        segments=[
            DetectedSegment(
                type=SegmentType.CHUNK,
                title="Full Document",
                content=content,
                start_offset=0,
                end_offset=len(content),
            )
        ],
        total_words=total_words,
        pattern_used=None,
    )


def _segment_by_patterns(
    content: str,
    patterns: list,  # list[DetectedPattern]
    opts: SegmentationOptions,
) -> list[DetectedSegment]:
    """Segment content based on detected patterns."""
    segments: list[DetectedSegment] = []

    # Sort patterns by position
    sorted_patterns = sorted(patterns, key=lambda p: p.start_index)

    for i, current in enumerate(sorted_patterns):
        next_pattern = sorted_patterns[i + 1] if i + 1 < len(sorted_patterns) else None

        start_offset = current.start_index
        end_offset = next_pattern.start_index if next_pattern else len(content)

        # Extract content for this segment
        segment_content = content[start_offset:end_offset].strip()

        if not segment_content:
            continue

        word_count = count_words(segment_content)

        # If segment is too large, split into sub-chunks
        if word_count > opts.chunk_size * 2:
            sub_chunks = chunk_text(
                segment_content,
                ChunkOptions(
                    chunk_size=opts.chunk_size,
                    overlap=opts.overlap,
                    respect_paragraphs=True,
                ),
            )

            # First chunk gets the chapter title
            if sub_chunks:
                segments.append(
                    DetectedSegment(
                        type=current.pattern.segment_type,
                        title=current.title,
                        content=sub_chunks[0].content,
                        start_offset=start_offset + sub_chunks[0].start_offset,
                        end_offset=start_offset + sub_chunks[0].end_offset,
                    )
                )

                # Additional chunks are sub-segments
                for j, chunk in enumerate(sub_chunks[1:], 2):
                    segments.append(
                        DetectedSegment(
                            type=SegmentType.CHUNK,
                            title=f"{current.title} (part {j})",
                            content=chunk.content,
                            start_offset=start_offset + chunk.start_offset,
                            end_offset=start_offset + chunk.end_offset,
                        )
                    )
        else:
            segments.append(
                DetectedSegment(
                    type=current.pattern.segment_type,
                    title=current.title,
                    content=segment_content,
                    start_offset=start_offset,
                    end_offset=end_offset,
                )
            )

    # Handle content before the first pattern (preamble/introduction)
    if sorted_patterns and sorted_patterns[0].start_index > 0:
        preamble_content = content[: sorted_patterns[0].start_index].strip()
        if count_words(preamble_content) >= opts.min_chapter_size / 2:
            segments.insert(
                0,
                DetectedSegment(
                    type=SegmentType.SECTION,
                    title="Introduction",
                    content=preamble_content,
                    start_offset=0,
                    end_offset=sorted_patterns[0].start_index,
                ),
            )

    return segments

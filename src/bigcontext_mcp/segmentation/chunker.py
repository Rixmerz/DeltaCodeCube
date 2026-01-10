"""Text chunking with overlap support."""

from dataclasses import dataclass, field


@dataclass
class Chunk:
    """A chunk of text with metadata."""

    content: str
    word_count: int
    start_offset: int
    end_offset: int


@dataclass
class ChunkOptions:
    """Options for text chunking."""

    chunk_size: int = 2000  # words
    overlap: int = 100  # words
    respect_paragraphs: bool = True


def count_words(text: str) -> int:
    """Count words in text."""
    return len([w for w in text.split() if w])


def split_into_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs."""
    import re

    paragraphs = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paragraphs if p.strip()]


def chunk_text(text: str, options: ChunkOptions | None = None) -> list[Chunk]:
    """Split text into chunks with optional overlap."""
    opts = options or ChunkOptions()

    if opts.respect_paragraphs:
        return _chunk_by_paragraphs(text, opts)

    return _chunk_by_words(text, opts)


def _chunk_by_paragraphs(text: str, opts: ChunkOptions) -> list[Chunk]:
    """Chunk text respecting paragraph boundaries."""
    paragraphs = split_into_paragraphs(text)
    chunks: list[Chunk] = []

    current_content = ""
    current_word_count = 0
    current_start_offset = 0
    last_end_offset = 0

    # Track position in original text
    search_start = 0

    for paragraph in paragraphs:
        paragraph_word_count = count_words(paragraph)

        # Find the paragraph position in original text
        paragraph_start = text.find(paragraph, search_start)
        if paragraph_start == -1:
            paragraph_start = search_start
        paragraph_end = paragraph_start + len(paragraph)
        search_start = paragraph_end

        # If this single paragraph exceeds chunk size, split it
        if paragraph_word_count > opts.chunk_size:
            # First, flush current chunk if any
            if current_content:
                chunks.append(
                    Chunk(
                        content=current_content.strip(),
                        word_count=current_word_count,
                        start_offset=current_start_offset,
                        end_offset=last_end_offset,
                    )
                )
                current_content = ""
                current_word_count = 0

            # Split the large paragraph by words
            sub_chunks = _chunk_by_words(paragraph, opts)
            for sub_chunk in sub_chunks:
                chunks.append(
                    Chunk(
                        content=sub_chunk.content,
                        word_count=sub_chunk.word_count,
                        start_offset=paragraph_start + sub_chunk.start_offset,
                        end_offset=paragraph_start + sub_chunk.end_offset,
                    )
                )
            current_start_offset = paragraph_end
            continue

        # Check if adding this paragraph exceeds chunk size
        if (
            current_word_count + paragraph_word_count > opts.chunk_size
            and current_content
        ):
            # Save current chunk
            chunks.append(
                Chunk(
                    content=current_content.strip(),
                    word_count=current_word_count,
                    start_offset=current_start_offset,
                    end_offset=last_end_offset,
                )
            )

            # Start new chunk with overlap
            if opts.overlap > 0 and current_content:
                overlap_words = _get_last_n_words(current_content, opts.overlap)
                current_content = overlap_words + "\n\n" + paragraph
                current_word_count = count_words(current_content)
            else:
                current_content = paragraph
                current_word_count = paragraph_word_count
            current_start_offset = paragraph_start
        else:
            # Add to current chunk
            if not current_content:
                current_start_offset = paragraph_start
            current_content += ("\n\n" if current_content else "") + paragraph
            current_word_count += paragraph_word_count

        last_end_offset = paragraph_end

    # Don't forget the last chunk
    if current_content:
        chunks.append(
            Chunk(
                content=current_content.strip(),
                word_count=current_word_count,
                start_offset=current_start_offset,
                end_offset=last_end_offset,
            )
        )

    return chunks


def _chunk_by_words(text: str, opts: ChunkOptions) -> list[Chunk]:
    """Chunk text by word count."""
    words = [w for w in text.split() if w]
    chunks: list[Chunk] = []

    current_words: list[str] = []
    start_word_index = 0

    for i, word in enumerate(words):
        current_words.append(word)

        if len(current_words) >= opts.chunk_size:
            content = " ".join(current_words)

            # Calculate approximate offsets
            start_offset = _calculate_offset(words, 0, start_word_index)
            end_offset = _calculate_offset(words, 0, i + 1)

            chunks.append(
                Chunk(
                    content=content,
                    word_count=len(current_words),
                    start_offset=start_offset,
                    end_offset=end_offset,
                )
            )

            # Handle overlap
            if opts.overlap > 0:
                current_words = current_words[-opts.overlap :]
                start_word_index = i + 1 - opts.overlap
            else:
                current_words = []
                start_word_index = i + 1

    # Handle remaining words
    if current_words:
        content = " ".join(current_words)
        start_offset = _calculate_offset(words, 0, start_word_index)
        end_offset = _calculate_offset(words, 0, len(words))

        chunks.append(
            Chunk(
                content=content,
                word_count=len(current_words),
                start_offset=start_offset,
                end_offset=end_offset,
            )
        )

    return chunks


def _calculate_offset(words: list[str], base_offset: int, word_index: int) -> int:
    """Calculate character offset for a word index."""
    offset = base_offset
    for i in range(min(word_index, len(words))):
        offset += len(words[i]) + 1  # +1 for space
    return offset


def _get_last_n_words(text: str, n: int) -> str:
    """Get the last n words from text."""
    words = [w for w in text.split() if w]
    return " ".join(words[-n:])

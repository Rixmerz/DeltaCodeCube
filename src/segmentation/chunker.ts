export interface Chunk {
  content: string;
  wordCount: number;
  startOffset: number;
  endOffset: number;
}

export interface ChunkOptions {
  chunkSize: number;
  overlap: number;
  respectParagraphs: boolean;
}

const DEFAULT_OPTIONS: ChunkOptions = {
  chunkSize: 2000,
  overlap: 100,
  respectParagraphs: true,
};

export function countWords(text: string): number {
  return text
    .split(/\s+/)
    .filter(word => word.length > 0)
    .length;
}

export function splitIntoParagraphs(text: string): string[] {
  // Split by double newlines or multiple newlines
  return text
    .split(/\n\s*\n/)
    .map(p => p.trim())
    .filter(p => p.length > 0);
}

export function chunkText(text: string, options: Partial<ChunkOptions> = {}): Chunk[] {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  const chunks: Chunk[] = [];

  if (opts.respectParagraphs) {
    return chunkByParagraphs(text, opts);
  }

  return chunkByWords(text, opts);
}

function chunkByParagraphs(text: string, opts: ChunkOptions): Chunk[] {
  const paragraphs = splitIntoParagraphs(text);
  const chunks: Chunk[] = [];

  let currentContent = '';
  let currentWordCount = 0;
  let currentStartOffset = 0;
  let lastEndOffset = 0;

  // Track position in original text
  let searchStart = 0;

  for (const paragraph of paragraphs) {
    const paragraphWordCount = countWords(paragraph);

    // Find the paragraph position in original text
    const paragraphStart = text.indexOf(paragraph, searchStart);
    const paragraphEnd = paragraphStart + paragraph.length;
    searchStart = paragraphEnd;

    // If this single paragraph exceeds chunk size, split it
    if (paragraphWordCount > opts.chunkSize) {
      // First, flush current chunk if any
      if (currentContent.length > 0) {
        chunks.push({
          content: currentContent.trim(),
          wordCount: currentWordCount,
          startOffset: currentStartOffset,
          endOffset: lastEndOffset,
        });
        currentContent = '';
        currentWordCount = 0;
      }

      // Split the large paragraph by words
      const subChunks = chunkByWords(paragraph, opts);
      for (const subChunk of subChunks) {
        chunks.push({
          content: subChunk.content,
          wordCount: subChunk.wordCount,
          startOffset: paragraphStart + subChunk.startOffset,
          endOffset: paragraphStart + subChunk.endOffset,
        });
      }
      currentStartOffset = paragraphEnd;
      continue;
    }

    // Check if adding this paragraph exceeds chunk size
    if (currentWordCount + paragraphWordCount > opts.chunkSize && currentContent.length > 0) {
      // Save current chunk
      chunks.push({
        content: currentContent.trim(),
        wordCount: currentWordCount,
        startOffset: currentStartOffset,
        endOffset: lastEndOffset,
      });

      // Start new chunk with overlap
      if (opts.overlap > 0 && currentContent.length > 0) {
        const overlapWords = getLastNWords(currentContent, opts.overlap);
        currentContent = overlapWords + '\n\n' + paragraph;
        currentWordCount = countWords(currentContent);
      } else {
        currentContent = paragraph;
        currentWordCount = paragraphWordCount;
      }
      currentStartOffset = paragraphStart;
    } else {
      // Add to current chunk
      if (currentContent.length === 0) {
        currentStartOffset = paragraphStart;
      }
      currentContent += (currentContent.length > 0 ? '\n\n' : '') + paragraph;
      currentWordCount += paragraphWordCount;
    }

    lastEndOffset = paragraphEnd;
  }

  // Don't forget the last chunk
  if (currentContent.length > 0) {
    chunks.push({
      content: currentContent.trim(),
      wordCount: currentWordCount,
      startOffset: currentStartOffset,
      endOffset: lastEndOffset,
    });
  }

  return chunks;
}

function chunkByWords(text: string, opts: ChunkOptions): Chunk[] {
  const words = text.split(/\s+/).filter(w => w.length > 0);
  const chunks: Chunk[] = [];

  let currentWords: string[] = [];
  let startWordIndex = 0;

  for (let i = 0; i < words.length; i++) {
    currentWords.push(words[i]);

    if (currentWords.length >= opts.chunkSize) {
      const content = currentWords.join(' ');

      // Calculate approximate offsets
      const startOffset = calculateOffset(words, 0, startWordIndex);
      const endOffset = calculateOffset(words, 0, i + 1);

      chunks.push({
        content,
        wordCount: currentWords.length,
        startOffset,
        endOffset,
      });

      // Handle overlap
      if (opts.overlap > 0) {
        currentWords = currentWords.slice(-opts.overlap);
        startWordIndex = i + 1 - opts.overlap;
      } else {
        currentWords = [];
        startWordIndex = i + 1;
      }
    }
  }

  // Handle remaining words
  if (currentWords.length > 0) {
    const content = currentWords.join(' ');
    const startOffset = calculateOffset(words, 0, startWordIndex);
    const endOffset = calculateOffset(words, 0, words.length);

    chunks.push({
      content,
      wordCount: currentWords.length,
      startOffset,
      endOffset,
    });
  }

  return chunks;
}

function calculateOffset(words: string[], baseOffset: number, wordIndex: number): number {
  let offset = baseOffset;
  for (let i = 0; i < wordIndex && i < words.length; i++) {
    offset += words[i].length + 1; // +1 for space
  }
  return offset;
}

function getLastNWords(text: string, n: number): string {
  const words = text.split(/\s+/).filter(w => w.length > 0);
  return words.slice(-n).join(' ');
}

import type { DetectedSegment, SegmentType } from '../types/index.js';
import { detectPatterns, filterBestPatterns, type DetectedPattern } from './patterns.js';
import { chunkText, countWords, type ChunkOptions } from './chunker.js';

export interface SegmentationOptions {
  chunkSize: number;
  overlap: number;
  minChapterSize: number;
  fallbackToChunks: boolean;
}

const DEFAULT_OPTIONS: SegmentationOptions = {
  chunkSize: 2000,
  overlap: 100,
  minChapterSize: 500,
  fallbackToChunks: true,
};

export interface SegmentationResult {
  segments: DetectedSegment[];
  totalWords: number;
  patternUsed: string | null;
}

export function segmentDocument(content: string, options: Partial<SegmentationOptions> = {}): SegmentationResult {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  const totalWords = countWords(content);

  // Step 1: Try to detect chapter/section patterns
  const allPatterns = detectPatterns(content);
  const bestPatterns = filterBestPatterns(allPatterns);

  // If we found good patterns, segment by them
  if (bestPatterns.length > 0) {
    const segments = segmentByPatterns(content, bestPatterns, opts);
    if (segments.length > 0) {
      return {
        segments,
        totalWords,
        patternUsed: bestPatterns[0].pattern.name,
      };
    }
  }

  // Step 2: Fallback to fixed-size chunking
  if (opts.fallbackToChunks) {
    const chunks = chunkText(content, {
      chunkSize: opts.chunkSize,
      overlap: opts.overlap,
      respectParagraphs: true,
    });

    const segments: DetectedSegment[] = chunks.map((chunk, index) => ({
      type: 'chunk' as SegmentType,
      title: `Chunk ${index + 1}`,
      content: chunk.content,
      startOffset: chunk.startOffset,
      endOffset: chunk.endOffset,
    }));

    return {
      segments,
      totalWords,
      patternUsed: 'fallback_chunks',
    };
  }

  // No segmentation possible
  return {
    segments: [{
      type: 'chunk' as SegmentType,
      title: 'Full Document',
      content,
      startOffset: 0,
      endOffset: content.length,
    }],
    totalWords,
    patternUsed: null,
  };
}

function segmentByPatterns(
  content: string,
  patterns: DetectedPattern[],
  opts: SegmentationOptions
): DetectedSegment[] {
  const segments: DetectedSegment[] = [];

  // Sort patterns by position
  const sortedPatterns = [...patterns].sort((a, b) => a.startIndex - b.startIndex);

  for (let i = 0; i < sortedPatterns.length; i++) {
    const current = sortedPatterns[i];
    const next = sortedPatterns[i + 1];

    const startOffset = current.startIndex;
    const endOffset = next ? next.startIndex : content.length;

    // Extract content for this segment
    const segmentContent = content.slice(startOffset, endOffset).trim();

    if (segmentContent.length === 0) continue;

    const wordCount = countWords(segmentContent);

    // If segment is too large, split into sub-chunks
    if (wordCount > opts.chunkSize * 2) {
      const subChunks = chunkText(segmentContent, {
        chunkSize: opts.chunkSize,
        overlap: opts.overlap,
        respectParagraphs: true,
      });

      // First chunk gets the chapter title
      segments.push({
        type: current.pattern.type,
        title: current.title,
        content: subChunks[0]?.content || segmentContent,
        startOffset: startOffset + (subChunks[0]?.startOffset || 0),
        endOffset: startOffset + (subChunks[0]?.endOffset || segmentContent.length),
      });

      // Additional chunks are sub-segments
      for (let j = 1; j < subChunks.length; j++) {
        segments.push({
          type: 'chunk' as SegmentType,
          title: `${current.title} (part ${j + 1})`,
          content: subChunks[j].content,
          startOffset: startOffset + subChunks[j].startOffset,
          endOffset: startOffset + subChunks[j].endOffset,
        });
      }
    } else {
      segments.push({
        type: current.pattern.type,
        title: current.title,
        content: segmentContent,
        startOffset,
        endOffset,
      });
    }
  }

  // Handle content before the first pattern (preamble/introduction)
  if (sortedPatterns.length > 0 && sortedPatterns[0].startIndex > 0) {
    const preambleContent = content.slice(0, sortedPatterns[0].startIndex).trim();
    if (countWords(preambleContent) >= opts.minChapterSize / 2) {
      segments.unshift({
        type: 'section' as SegmentType,
        title: 'Introduction',
        content: preambleContent,
        startOffset: 0,
        endOffset: sortedPatterns[0].startIndex,
      });
    }
  }

  return segments;
}

export { countWords };

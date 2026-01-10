import type { SegmentType } from '../types/index.js';

export interface ChapterPattern {
  name: string;
  regex: RegExp;
  confidence: number;
  type: SegmentType;
  extractTitle: (match: RegExpMatchArray) => string | null;
}

export const CHAPTER_PATTERNS: ChapterPattern[] = [
  // "Chapter 1: Title" or "CHAPTER I"
  {
    name: 'numbered_chapter',
    regex: /^(?:Chapter|CHAPTER|Capitulo|CAPITULO)\s+(\d+|[IVXLCDM]+)(?:\s*[:\.\-—]\s*(.+))?$/m,
    confidence: 0.95,
    type: 'chapter',
    extractTitle: (m) => m[2]?.trim() || `Chapter ${m[1]}`,
  },
  // "Part 1: Title" or "PART II"
  {
    name: 'part',
    regex: /^(?:Part|PART|Parte|PARTE)\s+(\d+|[IVXLCDM]+)(?:\s*[:\.\-—]\s*(.+))?$/m,
    confidence: 0.9,
    type: 'chapter',
    extractTitle: (m) => m[2]?.trim() || `Part ${m[1]}`,
  },
  // "Book 1" or "BOOK I"
  {
    name: 'book',
    regex: /^(?:Book|BOOK|Libro|LIBRO)\s+(\d+|[IVXLCDM]+)(?:\s*[:\.\-—]\s*(.+))?$/m,
    confidence: 0.9,
    type: 'chapter',
    extractTitle: (m) => m[2]?.trim() || `Book ${m[1]}`,
  },
  // Markdown H1: "# Title"
  {
    name: 'markdown_h1',
    regex: /^#\s+(.+)$/m,
    confidence: 0.85,
    type: 'chapter',
    extractTitle: (m) => m[1].trim(),
  },
  // Markdown H2: "## Title"
  {
    name: 'markdown_h2',
    regex: /^##\s+(.+)$/m,
    confidence: 0.7,
    type: 'section',
    extractTitle: (m) => m[1].trim(),
  },
  // Markdown H3: "### Title"
  {
    name: 'markdown_h3',
    regex: /^###\s+(.+)$/m,
    confidence: 0.6,
    type: 'section',
    extractTitle: (m) => m[1].trim(),
  },
  // Numbered section: "1.2.3 Title"
  {
    name: 'numbered_section',
    regex: /^(\d+(?:\.\d+)+)\s+(.+)$/m,
    confidence: 0.6,
    type: 'section',
    extractTitle: (m) => `${m[1]} ${m[2]}`,
  },
  // Simple numbered: "1. Title" at the start of a paragraph
  {
    name: 'simple_numbered',
    regex: /^(\d+)\.\s+([A-Z][^\n]{5,50})$/m,
    confidence: 0.5,
    type: 'section',
    extractTitle: (m) => `${m[1]}. ${m[2]}`,
  },
  // ALL CAPS TITLE (at least 3 words, all caps)
  {
    name: 'all_caps_title',
    regex: /^([A-Z][A-Z\s]{10,60})$/m,
    confidence: 0.4,
    type: 'chapter',
    extractTitle: (m) => m[1].trim(),
  },
  // Drama/Play: "Act I", "Scene 2"
  {
    name: 'dramatic',
    regex: /^(?:Act|ACT|Scene|SCENE|Acto|ACTO|Escena|ESCENA)\s+(\d+|[IVXLCDM]+)(?:\s*[:\.\-—]\s*(.+))?$/m,
    confidence: 0.9,
    type: 'chapter',
    extractTitle: (m) => m[2]?.trim() || m[0],
  },
  // Bible-style: "Genesis 1" or "Psalm 23"
  {
    name: 'bible_book',
    regex: /^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(\d+)$/m,
    confidence: 0.7,
    type: 'chapter',
    extractTitle: (m) => `${m[1]} ${m[2]}`,
  },
];

export interface DetectedPattern {
  pattern: ChapterPattern;
  match: RegExpMatchArray;
  startIndex: number;
  endIndex: number;
  title: string | null;
}

export function detectPatterns(content: string): DetectedPattern[] {
  const detected: DetectedPattern[] = [];
  const lines = content.split('\n');
  let charOffset = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmedLine = line.trim();

    if (trimmedLine.length === 0) {
      charOffset += line.length + 1;
      continue;
    }

    for (const pattern of CHAPTER_PATTERNS) {
      const match = trimmedLine.match(pattern.regex);
      if (match) {
        detected.push({
          pattern,
          match,
          startIndex: charOffset,
          endIndex: charOffset + line.length,
          title: pattern.extractTitle(match),
        });
        break; // Only match one pattern per line
      }
    }

    charOffset += line.length + 1;
  }

  // Sort by confidence (descending) then by position
  return detected.sort((a, b) => {
    if (a.pattern.confidence !== b.pattern.confidence) {
      return b.pattern.confidence - a.pattern.confidence;
    }
    return a.startIndex - b.startIndex;
  });
}

export function filterBestPatterns(detected: DetectedPattern[], minConfidence: number = 0.5): DetectedPattern[] {
  if (detected.length === 0) return [];

  // Group by pattern type
  const byType = new Map<string, DetectedPattern[]>();
  for (const d of detected) {
    const type = d.pattern.name;
    if (!byType.has(type)) {
      byType.set(type, []);
    }
    byType.get(type)!.push(d);
  }

  // Find the most common high-confidence pattern
  let bestType: string | null = null;
  let bestCount = 0;
  let bestConfidence = 0;

  for (const [type, items] of byType) {
    const confidence = items[0].pattern.confidence;
    if (confidence >= minConfidence) {
      if (items.length > bestCount || (items.length === bestCount && confidence > bestConfidence)) {
        bestType = type;
        bestCount = items.length;
        bestConfidence = confidence;
      }
    }
  }

  if (bestType === null) return [];

  // Return all detections of the best type, sorted by position
  return byType.get(bestType)!.sort((a, b) => a.startIndex - b.startIndex);
}

export type DocumentFormat = 'txt' | 'md' | 'pdf' | 'epub' | 'html';
export type SegmentType = 'chapter' | 'section' | 'paragraph' | 'chunk';

export interface Document {
  id: number;
  path: string;
  title: string;
  format: DocumentFormat;
  totalWords: number;
  totalSegments: number;
  fileHash: string;
  createdAt: string;
}

export interface Segment {
  id: number;
  documentId: number;
  parentSegmentId: number | null;
  type: SegmentType;
  title: string | null;
  content: string;
  wordCount: number;
  position: number;
}

export interface TermFrequency {
  segmentId: number;
  term: string;
  count: number;
  tf: number;
}

export interface DocumentFrequency {
  term: string;
  df: number;
  idf: number;
}

export interface IngestResult {
  success: boolean;
  documentId: number;
  title: string;
  format: DocumentFormat;
  totalSegments: number;
  totalWords: number;
  structure: SegmentInfo[];
  processingTimeMs: number;
}

export interface SegmentInfo {
  segmentId: number;
  type: SegmentType;
  title: string | null;
  wordCount: number;
  position: number;
}

export interface SearchResult {
  results: SearchResultItem[];
  totalMatches: number;
  queryTerms: string[];
}

export interface SearchResultItem {
  segmentId: number;
  documentId: number;
  documentTitle: string;
  segmentTitle: string | null;
  segmentType: SegmentType;
  score: number;
  snippet: string;
  matchedTerms: string[];
  position: number;
}

export interface MetadataResult {
  document?: DocumentInfo;
  segment?: SegmentMetadata;
  structure?: StructureItem[];
  topTerms?: TermScore[];
}

export interface DocumentInfo {
  id: number;
  path: string;
  title: string;
  format: DocumentFormat;
  totalWords: number;
  totalSegments: number;
  createdAt: string;
}

export interface SegmentMetadata {
  id: number;
  type: SegmentType;
  title: string | null;
  wordCount: number;
  position: number;
}

export interface StructureItem {
  segmentId: number;
  type: SegmentType;
  title: string | null;
  wordCount: number;
  depth: number;
}

export interface TermScore {
  term: string;
  score: number;
}

export interface CompareResult {
  segmentA: SegmentSummary;
  segmentB: SegmentSummary;
  similarityScore: number;
  sharedThemes: SharedTerm[];
  uniqueToA: TermScore[];
  uniqueToB: TermScore[];
  bridgeSegments?: BridgeSegment[];
}

export interface SegmentSummary {
  id: number;
  title: string | null;
  wordCount: number;
}

export interface SharedTerm {
  term: string;
  scoreA: number;
  scoreB: number;
}

export interface BridgeSegment {
  segmentId: number;
  title: string | null;
  connectionScore: number;
}

export interface ParsedDocument {
  content: string;
  metadata?: Record<string, unknown>;
}

export interface DetectedSegment {
  type: SegmentType;
  title: string | null;
  content: string;
  startOffset: number;
  endOffset: number;
}

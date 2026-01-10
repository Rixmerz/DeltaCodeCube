import Database from 'better-sqlite3';
import { tokenize, countTermFrequencies } from './tokenizer.js';
import {
  insertTermFrequencies,
  updateDocumentFrequencies,
  getDocumentFrequencies,
  searchSegmentsByTerms,
  type TermFrequencyParams,
} from '../db/queries/search.js';
import { getSegmentById } from '../db/queries/segments.js';
import { getDocumentById } from '../db/queries/documents.js';
import type { SearchResult, SearchResultItem, TermScore } from '../types/index.js';

export interface TfIdfOptions {
  minTermFrequency: number;
  maxTerms: number;
}

const DEFAULT_OPTIONS: TfIdfOptions = {
  minTermFrequency: 1,
  maxTerms: 1000,
};

/**
 * Index a segment's content for TF-IDF search
 */
export function indexSegment(
  db: Database.Database,
  segmentId: number,
  content: string,
  options: Partial<TfIdfOptions> = {}
): void {
  const opts = { ...DEFAULT_OPTIONS, ...options };

  // Tokenize and count frequencies
  const frequencies = countTermFrequencies(content);
  const totalTerms = Array.from(frequencies.values()).reduce((a, b) => a + b, 0);

  if (totalTerms === 0) return;

  // Calculate TF for each term
  const termFrequencies: TermFrequencyParams[] = [];

  for (const [term, count] of frequencies) {
    if (count >= opts.minTermFrequency) {
      const tf = count / totalTerms;
      termFrequencies.push({
        segmentId,
        term,
        count,
        tf,
      });
    }
  }

  // Limit number of terms if needed
  const sortedTerms = termFrequencies
    .sort((a, b) => b.count - a.count)
    .slice(0, opts.maxTerms);

  // Insert into database
  if (sortedTerms.length > 0) {
    insertTermFrequencies(db, sortedTerms);
  }
}

/**
 * Rebuild the IDF values after indexing changes
 */
export function rebuildIdf(db: Database.Database): void {
  updateDocumentFrequencies(db);
}

/**
 * Search for segments matching the query
 */
export function search(
  db: Database.Database,
  query: string,
  options: {
    documentId?: number;
    segmentId?: number;
    limit?: number;
    contextWords?: number;
  } = {}
): SearchResult {
  // Tokenize query
  const queryTerms = tokenize(query, { removeStopWords: true });

  if (queryTerms.length === 0) {
    return {
      results: [],
      totalMatches: 0,
      queryTerms: [],
    };
  }

  // Search for matching segments
  const matches = searchSegmentsByTerms(db, queryTerms, {
    documentId: options.documentId,
    segmentId: options.segmentId,
    limit: options.limit ?? 10,
  });

  // Build results with snippets
  const results: SearchResultItem[] = [];

  for (const match of matches) {
    const segment = getSegmentById(db, match.segmentId);
    if (!segment) continue;

    const document = getDocumentById(db, match.documentId);
    if (!document) continue;

    // Generate snippet around matched terms
    const snippet = generateSnippet(segment.content, match.matchedTerms, options.contextWords ?? 50);

    results.push({
      segmentId: match.segmentId,
      documentId: match.documentId,
      documentTitle: document.title,
      segmentTitle: segment.title,
      segmentType: segment.type,
      score: match.score,
      snippet,
      matchedTerms: match.matchedTerms,
      position: segment.position,
    });
  }

  return {
    results,
    totalMatches: results.length,
    queryTerms,
  };
}

/**
 * Generate a snippet around the first occurrence of any matched term
 */
function generateSnippet(content: string, matchedTerms: string[], contextWords: number): string {
  const words = content.split(/\s+/);
  const lowerContent = content.toLowerCase();

  // Find first occurrence of any matched term
  let firstMatchIndex = -1;
  let matchedTerm = '';

  for (const term of matchedTerms) {
    const termLower = term.toLowerCase();
    const index = lowerContent.indexOf(termLower);
    if (index !== -1 && (firstMatchIndex === -1 || index < firstMatchIndex)) {
      firstMatchIndex = index;
      matchedTerm = term;
    }
  }

  if (firstMatchIndex === -1) {
    // No match found, return beginning of content
    return words.slice(0, contextWords * 2).join(' ') + (words.length > contextWords * 2 ? '...' : '');
  }

  // Find word index at the match position
  let charCount = 0;
  let matchWordIndex = 0;
  for (let i = 0; i < words.length; i++) {
    if (charCount >= firstMatchIndex) {
      matchWordIndex = i;
      break;
    }
    charCount += words[i].length + 1;
  }

  // Extract context around the match
  const startIndex = Math.max(0, matchWordIndex - contextWords);
  const endIndex = Math.min(words.length, matchWordIndex + contextWords);

  let snippet = '';
  if (startIndex > 0) snippet += '...';
  snippet += words.slice(startIndex, endIndex).join(' ');
  if (endIndex < words.length) snippet += '...';

  return snippet;
}

/**
 * Get TF-IDF vector for a segment
 */
export function getSegmentVector(
  db: Database.Database,
  segmentId: number
): Map<string, number> {
  const vector = new Map<string, number>();

  const termFreqs = db.prepare(`
    SELECT term, tf FROM term_frequencies WHERE segment_id = ?
  `).all(segmentId) as Array<{ term: string; tf: number }>;

  const terms = termFreqs.map(t => t.term);
  const dfMap = getDocumentFrequencies(db, terms);

  for (const { term, tf } of termFreqs) {
    const df = dfMap.get(term);
    const idf = df?.idf ?? 1.0;
    vector.set(term, tf * idf);
  }

  return vector;
}

/**
 * Calculate cosine similarity between two TF-IDF vectors
 */
export function cosineSimilarity(
  vectorA: Map<string, number>,
  vectorB: Map<string, number>
): number {
  const allTerms = new Set([...vectorA.keys(), ...vectorB.keys()]);

  let dotProduct = 0;
  let magnitudeA = 0;
  let magnitudeB = 0;

  for (const term of allTerms) {
    const a = vectorA.get(term) ?? 0;
    const b = vectorB.get(term) ?? 0;

    dotProduct += a * b;
    magnitudeA += a * a;
    magnitudeB += b * b;
  }

  magnitudeA = Math.sqrt(magnitudeA);
  magnitudeB = Math.sqrt(magnitudeB);

  if (magnitudeA === 0 || magnitudeB === 0) return 0;

  return dotProduct / (magnitudeA * magnitudeB);
}

/**
 * Get top terms for a segment by TF-IDF score
 */
export function getTopTermsByTfIdf(
  db: Database.Database,
  segmentId: number,
  limit: number = 10
): TermScore[] {
  const vector = getSegmentVector(db, segmentId);

  return Array.from(vector.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([term, score]) => ({ term, score }));
}

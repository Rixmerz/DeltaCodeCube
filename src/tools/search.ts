import Database from 'better-sqlite3';
import type { SearchResult } from '../types/index.js';
import { SearchSegmentSchema } from '../types/schemas.js';
import { search } from '../search/tfidf.js';
import { Logger } from '../utils/logger.js';
import { ErrorHandler } from '../utils/errors.js';

export async function searchSegments(
  db: Database.Database,
  input: unknown,
  logger: Logger,
  errorHandler: ErrorHandler
): Promise<SearchResult> {
  try {
    // Validate input
    const params = SearchSegmentSchema.parse(input);

    logger.debug('Searching segments', {
      query: params.query,
      documentId: params.documentId,
      segmentId: params.segmentId,
      limit: params.limit,
    });

    // Perform search
    const result = search(db, params.query, {
      documentId: params.documentId,
      segmentId: params.segmentId,
      limit: params.limit,
      contextWords: params.contextWords,
    });

    logger.info('Search completed', {
      query: params.query,
      totalMatches: result.totalMatches,
      queryTerms: result.queryTerms,
    });

    return result;
  } catch (error) {
    return errorHandler.handleToolError(error, 'search_segment');
  }
}

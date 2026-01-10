import Database from 'better-sqlite3';
import type { MetadataResult, StructureItem } from '../types/index.js';
import { GetMetadataSchema } from '../types/schemas.js';
import { getDocumentById, listDocuments } from '../db/queries/documents.js';
import { getSegmentById, getDocumentStructure } from '../db/queries/segments.js';
import { getTopTermsByTfIdf } from '../search/tfidf.js';
import { Logger } from '../utils/logger.js';
import { ErrorHandler } from '../utils/errors.js';

export interface ListDocumentsResult {
  documents: Array<{
    id: number;
    path: string;
    title: string;
    format: string;
    totalWords: number;
    totalSegments: number;
    createdAt: string;
  }>;
  total: number;
}

export async function getMetadata(
  db: Database.Database,
  input: unknown,
  logger: Logger,
  errorHandler: ErrorHandler
): Promise<MetadataResult> {
  try {
    // Validate input
    const params = GetMetadataSchema.parse(input);

    const result: MetadataResult = {};

    // Get document info if documentId provided
    if (params.documentId) {
      const document = getDocumentById(db, params.documentId);
      if (!document) {
        throw errorHandler.createNotFoundError('Document', params.documentId);
      }

      result.document = {
        id: document.id,
        path: document.path,
        title: document.title,
        format: document.format,
        totalWords: document.totalWords,
        totalSegments: document.totalSegments,
        createdAt: document.createdAt,
      };

      // Get document structure if requested
      if (params.includeStructure) {
        const segments = getDocumentStructure(db, params.documentId);
        result.structure = segments.map((seg, index) => ({
          segmentId: seg.segmentId,
          type: seg.type,
          title: seg.title,
          wordCount: seg.wordCount,
          depth: seg.type === 'chapter' ? 0 : 1,
        }));
      }
    }

    // Get segment info if segmentId provided
    if (params.segmentId) {
      const segment = getSegmentById(db, params.segmentId);
      if (!segment) {
        throw errorHandler.createNotFoundError('Segment', params.segmentId);
      }

      result.segment = {
        id: segment.id,
        type: segment.type,
        title: segment.title,
        wordCount: segment.wordCount,
        position: segment.position,
      };

      // Get top terms for segment
      result.topTerms = getTopTermsByTfIdf(db, params.segmentId, params.topTerms);

      // If document not already loaded, get it for context
      if (!result.document) {
        const document = getDocumentById(db, segment.documentId);
        if (document) {
          result.document = {
            id: document.id,
            path: document.path,
            title: document.title,
            format: document.format,
            totalWords: document.totalWords,
            totalSegments: document.totalSegments,
            createdAt: document.createdAt,
          };
        }
      }
    }

    // If neither documentId nor segmentId provided, return summary
    if (!params.documentId && !params.segmentId) {
      throw errorHandler.createInvalidParamsError('Either documentId or segmentId must be provided');
    }

    logger.debug('Metadata retrieved', {
      documentId: params.documentId,
      segmentId: params.segmentId,
    });

    return result;
  } catch (error) {
    return errorHandler.handleToolError(error, 'get_metadata');
  }
}

export async function getDocumentsList(
  db: Database.Database,
  input: unknown,
  logger: Logger,
  errorHandler: ErrorHandler
): Promise<ListDocumentsResult> {
  try {
    const params = input as { limit?: number; offset?: number };
    const limit = params.limit ?? 20;
    const offset = params.offset ?? 0;

    const documents = listDocuments(db, limit, offset);

    // Get total count
    const totalResult = db.prepare('SELECT COUNT(*) as count FROM documents').get() as { count: number };

    logger.debug('Documents listed', { count: documents.length, total: totalResult.count });

    return {
      documents: documents.map(d => ({
        id: d.id,
        path: d.path,
        title: d.title,
        format: d.format,
        totalWords: d.totalWords,
        totalSegments: d.totalSegments,
        createdAt: d.createdAt,
      })),
      total: totalResult.count,
    };
  } catch (error) {
    return errorHandler.handleToolError(error, 'list_documents');
  }
}

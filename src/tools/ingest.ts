import Database from 'better-sqlite3';
import fs from 'fs/promises';
import crypto from 'crypto';
import path from 'path';
import type { IngestResult, SegmentInfo } from '../types/index.js';
import { IngestDocumentSchema, type IngestDocumentInput } from '../types/schemas.js';
import { parseDocument, detectFormat } from '../parsers/index.js';
import { segmentDocument } from '../segmentation/segmenter.js';
import { countWords } from '../segmentation/chunker.js';
import {
  createDocument,
  getDocumentByPath,
  updateDocumentStats,
  deleteDocument,
} from '../db/queries/documents.js';
import { createSegmentsBatch, deleteSegmentsByDocumentId } from '../db/queries/segments.js';
import { deleteTermFrequenciesForDocument } from '../db/queries/search.js';
import { indexSegment, rebuildIdf } from '../search/tfidf.js';
import { Logger } from '../utils/logger.js';
import { ErrorHandler } from '../utils/errors.js';

export async function ingestDocument(
  db: Database.Database,
  input: unknown,
  logger: Logger,
  errorHandler: ErrorHandler
): Promise<IngestResult> {
  const startTime = Date.now();

  try {
    // Validate input
    const params = IngestDocumentSchema.parse(input);

    // Check if file exists
    const absolutePath = path.resolve(params.path);
    try {
      await fs.access(absolutePath);
    } catch {
      throw errorHandler.createInvalidParamsError(`File not found: ${absolutePath}`);
    }

    // Detect format
    const format = detectFormat(absolutePath);
    if (!format) {
      throw errorHandler.createInvalidParamsError(`Unsupported file format: ${path.extname(absolutePath)}`);
    }

    // Calculate file hash
    const fileContent = await fs.readFile(absolutePath);
    const fileHash = crypto.createHash('md5').update(fileContent).digest('hex');

    // Check if document already exists
    const existingDoc = getDocumentByPath(db, absolutePath);
    if (existingDoc) {
      if (!params.force && existingDoc.fileHash === fileHash) {
        logger.info('Document already indexed with same hash', { path: absolutePath });
        return {
          success: true,
          documentId: existingDoc.id,
          title: existingDoc.title,
          format: existingDoc.format,
          totalSegments: existingDoc.totalSegments,
          totalWords: existingDoc.totalWords,
          structure: [],
          processingTimeMs: Date.now() - startTime,
        };
      }

      // Delete existing document data for re-indexing
      logger.info('Re-indexing existing document', { path: absolutePath });
      deleteTermFrequenciesForDocument(db, existingDoc.id);
      deleteSegmentsByDocumentId(db, existingDoc.id);
      deleteDocument(db, existingDoc.id);
    }

    // Parse document
    logger.info('Parsing document', { path: absolutePath, format });
    const parsed = await parseDocument(absolutePath, format);

    // Extract title from params, metadata, or filename
    const title = params.title ||
      (parsed.metadata?.title as string) ||
      path.basename(absolutePath, path.extname(absolutePath));

    // Create document record
    const documentId = createDocument(db, {
      path: absolutePath,
      title,
      format,
      fileHash,
    });

    // Segment the document
    logger.info('Segmenting document', { documentId, chunkSize: params.chunkSize });
    const segmentationResult = segmentDocument(parsed.content, {
      chunkSize: params.chunkSize,
      overlap: params.overlap,
    });

    // Create segment records
    const segmentParams = segmentationResult.segments.map((seg, index) => ({
      documentId,
      parentSegmentId: null,
      type: seg.type,
      title: seg.title,
      content: seg.content,
      wordCount: countWords(seg.content),
      position: index,
      startOffset: seg.startOffset,
      endOffset: seg.endOffset,
    }));

    const segmentIds = createSegmentsBatch(db, segmentParams);

    // Index each segment for search
    logger.info('Indexing segments for search', { count: segmentIds.length });
    for (let i = 0; i < segmentIds.length; i++) {
      indexSegment(db, segmentIds[i], segmentationResult.segments[i].content);
    }

    // Rebuild IDF after indexing
    rebuildIdf(db);

    // Update document stats
    const totalWords = segmentParams.reduce((sum, s) => sum + s.wordCount, 0);
    updateDocumentStats(db, documentId, totalWords, segmentIds.length);

    // Build structure info
    const structure: SegmentInfo[] = segmentParams.map((seg, index) => ({
      segmentId: segmentIds[index],
      type: seg.type,
      title: seg.title,
      wordCount: seg.wordCount,
      position: seg.position,
    }));

    logger.info('Document ingested successfully', {
      documentId,
      totalSegments: segmentIds.length,
      totalWords,
      patternUsed: segmentationResult.patternUsed,
    });

    return {
      success: true,
      documentId,
      title,
      format,
      totalSegments: segmentIds.length,
      totalWords,
      structure,
      processingTimeMs: Date.now() - startTime,
    };
  } catch (error) {
    return errorHandler.handleToolError(error, 'ingest_document');
  }
}

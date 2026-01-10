import Database from 'better-sqlite3';
import type { CompareResult, SharedTerm, TermScore, BridgeSegment } from '../types/index.js';
import { CompareSegmentsSchema } from '../types/schemas.js';
import { getSegmentById, getSegmentsByDocumentId } from '../db/queries/segments.js';
import { getSegmentVector, cosineSimilarity, getTopTermsByTfIdf } from '../search/tfidf.js';
import { Logger } from '../utils/logger.js';
import { ErrorHandler } from '../utils/errors.js';

export async function compareSegments(
  db: Database.Database,
  input: unknown,
  logger: Logger,
  errorHandler: ErrorHandler
): Promise<CompareResult> {
  try {
    // Validate input
    const params = CompareSegmentsSchema.parse(input);

    // Get both segments
    const segmentA = getSegmentById(db, params.segmentIdA);
    const segmentB = getSegmentById(db, params.segmentIdB);

    if (!segmentA) {
      throw errorHandler.createNotFoundError('Segment A', params.segmentIdA);
    }
    if (!segmentB) {
      throw errorHandler.createNotFoundError('Segment B', params.segmentIdB);
    }

    // Get TF-IDF vectors
    const vectorA = getSegmentVector(db, params.segmentIdA);
    const vectorB = getSegmentVector(db, params.segmentIdB);

    // Calculate similarity
    const similarityScore = cosineSimilarity(vectorA, vectorB);

    // Find shared themes (terms that appear in both with significant score)
    const sharedThemes: SharedTerm[] = [];
    const uniqueToA: TermScore[] = [];
    const uniqueToB: TermScore[] = [];

    const threshold = 0.01;

    for (const [term, scoreA] of vectorA) {
      const scoreB = vectorB.get(term);
      if (scoreB !== undefined && scoreB > threshold && scoreA > threshold) {
        sharedThemes.push({ term, scoreA, scoreB });
      } else if (scoreA > threshold) {
        uniqueToA.push({ term, score: scoreA });
      }
    }

    for (const [term, scoreB] of vectorB) {
      if (!vectorA.has(term) && scoreB > threshold) {
        uniqueToB.push({ term, score: scoreB });
      }
    }

    // Sort by score
    sharedThemes.sort((a, b) => (b.scoreA + b.scoreB) - (a.scoreA + a.scoreB));
    uniqueToA.sort((a, b) => b.score - a.score);
    uniqueToB.sort((a, b) => b.score - a.score);

    // Limit results
    const topShared = sharedThemes.slice(0, 10);
    const topUniqueA = uniqueToA.slice(0, 10);
    const topUniqueB = uniqueToB.slice(0, 10);

    // Find bridge segments if requested and segments are from the same document
    let bridgeSegments: BridgeSegment[] | undefined;

    if (params.findBridges && segmentA.documentId === segmentB.documentId) {
      bridgeSegments = findBridgeSegments(
        db,
        segmentA,
        segmentB,
        vectorA,
        vectorB,
        params.maxBridges ?? 3
      );
    }

    logger.info('Segments compared', {
      segmentIdA: params.segmentIdA,
      segmentIdB: params.segmentIdB,
      similarityScore,
      sharedThemesCount: topShared.length,
    });

    return {
      segmentA: {
        id: segmentA.id,
        title: segmentA.title,
        wordCount: segmentA.wordCount,
      },
      segmentB: {
        id: segmentB.id,
        title: segmentB.title,
        wordCount: segmentB.wordCount,
      },
      similarityScore,
      sharedThemes: topShared,
      uniqueToA: topUniqueA,
      uniqueToB: topUniqueB,
      bridgeSegments,
    };
  } catch (error) {
    return errorHandler.handleToolError(error, 'compare_segments');
  }
}

function findBridgeSegments(
  db: Database.Database,
  segmentA: { id: number; documentId: number; position: number },
  segmentB: { id: number; documentId: number; position: number },
  vectorA: Map<string, number>,
  vectorB: Map<string, number>,
  maxBridges: number
): BridgeSegment[] {
  // Get all segments from the document
  const allSegments = getSegmentsByDocumentId(db, segmentA.documentId);

  // Find segments between A and B
  const minPos = Math.min(segmentA.position, segmentB.position);
  const maxPos = Math.max(segmentA.position, segmentB.position);

  const betweenSegments = allSegments.filter(
    s => s.position > minPos && s.position < maxPos && s.id !== segmentA.id && s.id !== segmentB.id
  );

  if (betweenSegments.length === 0) {
    return [];
  }

  // Calculate connection score for each intermediate segment
  const scored: Array<{ segment: typeof betweenSegments[0]; score: number }> = [];

  for (const segment of betweenSegments) {
    const vectorBridge = getSegmentVector(db, segment.id);

    // Connection score = average similarity to both endpoints
    const simToA = cosineSimilarity(vectorBridge, vectorA);
    const simToB = cosineSimilarity(vectorBridge, vectorB);
    const connectionScore = (simToA + simToB) / 2;

    scored.push({ segment, score: connectionScore });
  }

  // Sort by connection score and return top bridges
  scored.sort((a, b) => b.score - a.score);

  return scored.slice(0, maxBridges).map(s => ({
    segmentId: s.segment.id,
    title: s.segment.title,
    connectionScore: s.score,
  }));
}

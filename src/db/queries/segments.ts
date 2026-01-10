import Database from 'better-sqlite3';
import type { Segment, SegmentType, SegmentInfo } from '../../types/index.js';

export interface CreateSegmentParams {
  documentId: number;
  parentSegmentId: number | null;
  type: SegmentType;
  title: string | null;
  content: string;
  wordCount: number;
  position: number;
  startOffset?: number;
  endOffset?: number;
}

export function createSegment(db: Database.Database, params: CreateSegmentParams): number {
  const stmt = db.prepare(`
    INSERT INTO segments (document_id, parent_segment_id, type, title, content, word_count, position, start_offset, end_offset)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);
  const result = stmt.run(
    params.documentId,
    params.parentSegmentId,
    params.type,
    params.title,
    params.content,
    params.wordCount,
    params.position,
    params.startOffset ?? null,
    params.endOffset ?? null
  );
  return result.lastInsertRowid as number;
}

export function createSegmentsBatch(db: Database.Database, segments: CreateSegmentParams[]): number[] {
  const stmt = db.prepare(`
    INSERT INTO segments (document_id, parent_segment_id, type, title, content, word_count, position, start_offset, end_offset)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);

  const insertMany = db.transaction((segs: CreateSegmentParams[]) => {
    const ids: number[] = [];
    for (const seg of segs) {
      const result = stmt.run(
        seg.documentId,
        seg.parentSegmentId,
        seg.type,
        seg.title,
        seg.content,
        seg.wordCount,
        seg.position,
        seg.startOffset ?? null,
        seg.endOffset ?? null
      );
      ids.push(result.lastInsertRowid as number);
    }
    return ids;
  });

  return insertMany(segments);
}

export function getSegmentById(db: Database.Database, id: number): Segment | undefined {
  const stmt = db.prepare(`
    SELECT id, document_id as documentId, parent_segment_id as parentSegmentId,
           type, title, content, word_count as wordCount, position
    FROM segments WHERE id = ?
  `);
  return stmt.get(id) as Segment | undefined;
}

export function getSegmentsByDocumentId(db: Database.Database, documentId: number): Segment[] {
  const stmt = db.prepare(`
    SELECT id, document_id as documentId, parent_segment_id as parentSegmentId,
           type, title, content, word_count as wordCount, position
    FROM segments WHERE document_id = ?
    ORDER BY position
  `);
  return stmt.all(documentId) as Segment[];
}

export function getDocumentStructure(db: Database.Database, documentId: number): SegmentInfo[] {
  const stmt = db.prepare(`
    SELECT id as segmentId, type, title, word_count as wordCount, position
    FROM segments
    WHERE document_id = ? AND type IN ('chapter', 'section')
    ORDER BY position
  `);
  return stmt.all(documentId) as SegmentInfo[];
}

export function getChunksByParent(db: Database.Database, parentId: number): Segment[] {
  const stmt = db.prepare(`
    SELECT id, document_id as documentId, parent_segment_id as parentSegmentId,
           type, title, content, word_count as wordCount, position
    FROM segments
    WHERE parent_segment_id = ? AND type = 'chunk'
    ORDER BY position
  `);
  return stmt.all(parentId) as Segment[];
}

export function deleteSegmentsByDocumentId(db: Database.Database, documentId: number): void {
  const stmt = db.prepare('DELETE FROM segments WHERE document_id = ?');
  stmt.run(documentId);
}

export function countSegments(db: Database.Database, documentId?: number): number {
  if (documentId) {
    const stmt = db.prepare('SELECT COUNT(*) as count FROM segments WHERE document_id = ?');
    const result = stmt.get(documentId) as { count: number };
    return result.count;
  }
  const stmt = db.prepare('SELECT COUNT(*) as count FROM segments');
  const result = stmt.get() as { count: number };
  return result.count;
}

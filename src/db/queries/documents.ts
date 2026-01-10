import Database from 'better-sqlite3';
import type { Document, DocumentFormat } from '../../types/index.js';

export interface CreateDocumentParams {
  path: string;
  title: string;
  format: DocumentFormat;
  fileHash: string;
}

export function createDocument(db: Database.Database, params: CreateDocumentParams): number {
  const stmt = db.prepare(`
    INSERT INTO documents (path, title, format, file_hash)
    VALUES (?, ?, ?, ?)
  `);
  const result = stmt.run(params.path, params.title, params.format, params.fileHash);
  return result.lastInsertRowid as number;
}

export function getDocumentById(db: Database.Database, id: number): Document | undefined {
  const stmt = db.prepare(`
    SELECT id, path, title, format, total_words as totalWords,
           total_segments as totalSegments, file_hash as fileHash,
           created_at as createdAt
    FROM documents WHERE id = ?
  `);
  return stmt.get(id) as Document | undefined;
}

export function getDocumentByPath(db: Database.Database, path: string): Document | undefined {
  const stmt = db.prepare(`
    SELECT id, path, title, format, total_words as totalWords,
           total_segments as totalSegments, file_hash as fileHash,
           created_at as createdAt
    FROM documents WHERE path = ?
  `);
  return stmt.get(path) as Document | undefined;
}

export function listDocuments(db: Database.Database, limit: number = 20, offset: number = 0): Document[] {
  const stmt = db.prepare(`
    SELECT id, path, title, format, total_words as totalWords,
           total_segments as totalSegments, file_hash as fileHash,
           created_at as createdAt
    FROM documents
    ORDER BY created_at DESC
    LIMIT ? OFFSET ?
  `);
  return stmt.all(limit, offset) as Document[];
}

export function updateDocumentStats(
  db: Database.Database,
  documentId: number,
  totalWords: number,
  totalSegments: number
): void {
  const stmt = db.prepare(`
    UPDATE documents
    SET total_words = ?, total_segments = ?, updated_at = datetime('now')
    WHERE id = ?
  `);
  stmt.run(totalWords, totalSegments, documentId);
}

export function deleteDocument(db: Database.Database, documentId: number): boolean {
  const stmt = db.prepare('DELETE FROM documents WHERE id = ?');
  const result = stmt.run(documentId);
  return result.changes > 0;
}

export function documentExists(db: Database.Database, path: string): boolean {
  const stmt = db.prepare('SELECT 1 FROM documents WHERE path = ?');
  return stmt.get(path) !== undefined;
}

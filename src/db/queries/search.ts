import Database from 'better-sqlite3';
import type { TermFrequency, DocumentFrequency } from '../../types/index.js';

export interface TermFrequencyParams {
  segmentId: number;
  term: string;
  count: number;
  tf: number;
}

export function insertTermFrequencies(db: Database.Database, terms: TermFrequencyParams[]): void {
  const stmt = db.prepare(`
    INSERT OR REPLACE INTO term_frequencies (segment_id, term, count, tf)
    VALUES (?, ?, ?, ?)
  `);

  const insertMany = db.transaction((items: TermFrequencyParams[]) => {
    for (const item of items) {
      stmt.run(item.segmentId, item.term, item.count, item.tf);
    }
  });

  insertMany(terms);
}

export function getTermFrequenciesForSegment(db: Database.Database, segmentId: number): TermFrequency[] {
  const stmt = db.prepare(`
    SELECT segment_id as segmentId, term, count, tf
    FROM term_frequencies WHERE segment_id = ?
    ORDER BY tf DESC
  `);
  return stmt.all(segmentId) as TermFrequency[];
}

export function getTopTermsForSegment(db: Database.Database, segmentId: number, limit: number = 10): TermFrequency[] {
  const stmt = db.prepare(`
    SELECT segment_id as segmentId, term, count, tf
    FROM term_frequencies WHERE segment_id = ?
    ORDER BY tf DESC LIMIT ?
  `);
  return stmt.all(segmentId, limit) as TermFrequency[];
}

export function updateDocumentFrequencies(db: Database.Database): void {
  // Calculate document frequency for each term
  db.exec(`
    DELETE FROM document_frequencies;

    INSERT INTO document_frequencies (term, df, idf, updated_at)
    SELECT
      term,
      COUNT(DISTINCT segment_id) as df,
      0.0 as idf,
      datetime('now')
    FROM term_frequencies
    GROUP BY term;
  `);

  // Calculate IDF: log(N / (1 + df))
  const totalSegments = db.prepare('SELECT COUNT(*) as count FROM segments').get() as { count: number };
  const N = totalSegments.count;

  if (N > 0) {
    db.prepare(`
      UPDATE document_frequencies
      SET idf = ln(? * 1.0 / (1 + df))
    `).run(N);
  }
}

export function getDocumentFrequency(db: Database.Database, term: string): DocumentFrequency | undefined {
  const stmt = db.prepare(`
    SELECT term, df, idf FROM document_frequencies WHERE term = ?
  `);
  return stmt.get(term) as DocumentFrequency | undefined;
}

export function getDocumentFrequencies(db: Database.Database, terms: string[]): Map<string, DocumentFrequency> {
  const placeholders = terms.map(() => '?').join(',');
  const stmt = db.prepare(`
    SELECT term, df, idf FROM document_frequencies WHERE term IN (${placeholders})
  `);
  const results = stmt.all(...terms) as DocumentFrequency[];

  const map = new Map<string, DocumentFrequency>();
  for (const r of results) {
    map.set(r.term, r);
  }
  return map;
}

export function searchSegmentsByTerms(
  db: Database.Database,
  terms: string[],
  options: { documentId?: number; segmentId?: number; limit?: number }
): Array<{ segmentId: number; documentId: number; score: number; matchedTerms: string[] }> {
  if (terms.length === 0) return [];

  const placeholders = terms.map(() => '?').join(',');

  let whereClause = `tf.term IN (${placeholders})`;
  const params: (string | number)[] = [...terms];

  if (options.documentId) {
    whereClause += ' AND s.document_id = ?';
    params.push(options.documentId);
  }

  if (options.segmentId) {
    whereClause += ' AND s.id = ?';
    params.push(options.segmentId);
  }

  const limit = options.limit ?? 10;

  const stmt = db.prepare(`
    SELECT
      s.id as segmentId,
      s.document_id as documentId,
      SUM(tf.tf * COALESCE(df.idf, 1.0)) as score,
      GROUP_CONCAT(DISTINCT tf.term) as matchedTermsStr
    FROM segments s
    JOIN term_frequencies tf ON s.id = tf.segment_id
    LEFT JOIN document_frequencies df ON tf.term = df.term
    WHERE ${whereClause}
    GROUP BY s.id
    ORDER BY score DESC
    LIMIT ?
  `);

  params.push(limit);
  const results = stmt.all(...params) as Array<{
    segmentId: number;
    documentId: number;
    score: number;
    matchedTermsStr: string;
  }>;

  return results.map(r => ({
    segmentId: r.segmentId,
    documentId: r.documentId,
    score: r.score,
    matchedTerms: r.matchedTermsStr ? r.matchedTermsStr.split(',') : [],
  }));
}

export function deleteTermFrequenciesForDocument(db: Database.Database, documentId: number): void {
  const stmt = db.prepare(`
    DELETE FROM term_frequencies
    WHERE segment_id IN (SELECT id FROM segments WHERE document_id = ?)
  `);
  stmt.run(documentId);
}

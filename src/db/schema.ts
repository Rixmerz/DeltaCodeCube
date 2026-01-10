import Database from 'better-sqlite3';

export function initSchema(db: Database.Database): void {
  db.exec(`
    -- Documents table: Master record for each ingested document
    CREATE TABLE IF NOT EXISTS documents (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      path TEXT NOT NULL UNIQUE,
      title TEXT NOT NULL,
      format TEXT NOT NULL CHECK (format IN ('txt', 'md', 'pdf', 'epub', 'html')),
      total_words INTEGER NOT NULL DEFAULT 0,
      total_segments INTEGER NOT NULL DEFAULT 0,
      file_hash TEXT NOT NULL,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    );

    -- Segments table: Chapters, sections, and chunks
    CREATE TABLE IF NOT EXISTS segments (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      document_id INTEGER NOT NULL,
      parent_segment_id INTEGER,
      type TEXT NOT NULL CHECK (type IN ('chapter', 'section', 'paragraph', 'chunk')),
      text_type TEXT DEFAULT 'unknown' CHECK (text_type IN ('narrative', 'poetry', 'wisdom', 'prophecy', 'epistle', 'apocalyptic', 'law', 'genealogy', 'unknown')),
      title TEXT,
      content TEXT NOT NULL,
      word_count INTEGER NOT NULL,
      position INTEGER NOT NULL,
      start_offset INTEGER,
      end_offset INTEGER,
      created_at TEXT DEFAULT (datetime('now')),
      FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
      FOREIGN KEY (parent_segment_id) REFERENCES segments(id) ON DELETE CASCADE
    );

    -- Document vocabulary: Closed lexicon for vocabulary control
    CREATE TABLE IF NOT EXISTS document_vocabulary (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      document_id INTEGER NOT NULL,
      token TEXT NOT NULL,
      frequency INTEGER NOT NULL DEFAULT 1,
      FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
      UNIQUE(document_id, token)
    );

    -- Document metadata: Version control and constraints
    CREATE TABLE IF NOT EXISTS document_metadata (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      document_id INTEGER NOT NULL UNIQUE,
      version TEXT,
      language TEXT DEFAULT 'english',
      vocabulary_size INTEGER DEFAULT 0,
      vocabulary_built_at TEXT,
      cognitive_constraints_enabled INTEGER DEFAULT 1,
      cross_section_synthesis_allowed INTEGER DEFAULT 0,
      max_sections_per_response INTEGER DEFAULT 3,
      max_books_per_response INTEGER DEFAULT 2,
      FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
    );

    -- Term frequencies: For TF calculation per segment
    CREATE TABLE IF NOT EXISTS term_frequencies (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      segment_id INTEGER NOT NULL,
      term TEXT NOT NULL,
      count INTEGER NOT NULL,
      tf REAL NOT NULL,
      FOREIGN KEY (segment_id) REFERENCES segments(id) ON DELETE CASCADE,
      UNIQUE(segment_id, term)
    );

    -- Document frequencies: IDF calculation across corpus
    CREATE TABLE IF NOT EXISTS document_frequencies (
      term TEXT PRIMARY KEY,
      df INTEGER NOT NULL,
      idf REAL NOT NULL,
      updated_at TEXT DEFAULT (datetime('now'))
    );

    -- Performance indexes
    CREATE INDEX IF NOT EXISTS idx_segments_document ON segments(document_id);
    CREATE INDEX IF NOT EXISTS idx_segments_parent ON segments(parent_segment_id);
    CREATE INDEX IF NOT EXISTS idx_segments_type ON segments(type);
    CREATE INDEX IF NOT EXISTS idx_segments_text_type ON segments(text_type);
    CREATE INDEX IF NOT EXISTS idx_term_freq_segment ON term_frequencies(segment_id);
    CREATE INDEX IF NOT EXISTS idx_term_freq_term ON term_frequencies(term);
    CREATE INDEX IF NOT EXISTS idx_vocab_document ON document_vocabulary(document_id);
    CREATE INDEX IF NOT EXISTS idx_vocab_token ON document_vocabulary(token);
  `);
}

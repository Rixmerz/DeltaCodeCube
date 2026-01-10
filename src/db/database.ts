import Database from 'better-sqlite3';
import fs from 'fs';
import path from 'path';
import { initSchema } from './schema.js';

let db: Database.Database | null = null;

export function initDatabase(dbPath: string): Database.Database {
  if (db) return db;

  // Ensure data directory exists
  const dataDir = path.dirname(dbPath);
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
  }

  db = new Database(dbPath);

  // Optimizations for SQLite
  db.pragma('journal_mode = WAL');
  db.pragma('foreign_keys = ON');

  // Initialize schema
  initSchema(db);

  return db;
}

export function getDatabase(): Database.Database {
  if (!db) throw new Error('Database not initialized. Call initDatabase first.');
  return db;
}

export function closeDatabase(): void {
  if (db) {
    db.close();
    db = null;
  }
}

import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export const config = {
  server: {
    name: 'bigcontext-mcp',
    version: '1.0.0',
  },
  db: {
    path: process.env.BIGCONTEXT_DB_PATH || path.join(__dirname, '..', 'data', 'bigcontext.db'),
  },
  segmentation: {
    defaultChunkSize: 2000,
    defaultOverlap: 100,
    minChunkSize: 100,
    maxChunkSize: 10000,
  },
  search: {
    defaultLimit: 5,
    maxLimit: 50,
    defaultContextWords: 50,
  },
  logging: {
    level: (process.env.LOG_LEVEL || 'info') as 'debug' | 'info' | 'warn' | 'error',
  },
};

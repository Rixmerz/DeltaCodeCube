import fs from 'fs/promises';
import type { ParsedDocument } from '../types/index.js';

export async function parseTxt(filePath: string): Promise<ParsedDocument> {
  const content = await fs.readFile(filePath, 'utf-8');
  return {
    content,
    metadata: {
      encoding: 'utf-8',
      originalPath: filePath,
    },
  };
}

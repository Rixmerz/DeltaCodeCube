import path from 'path';
import type { ParsedDocument, DocumentFormat } from '../types/index.js';
import { parseTxt } from './txt-parser.js';
import { parseMd } from './md-parser.js';
import { parseHtml } from './html-parser.js';
import { parsePdf } from './pdf-parser.js';
import { parseEpub } from './epub-parser.js';

const EXTENSION_TO_FORMAT: Record<string, DocumentFormat> = {
  '.txt': 'txt',
  '.text': 'txt',
  '.md': 'md',
  '.markdown': 'md',
  '.html': 'html',
  '.htm': 'html',
  '.xhtml': 'html',
  '.pdf': 'pdf',
  '.epub': 'epub',
};

export function detectFormat(filePath: string): DocumentFormat | null {
  const ext = path.extname(filePath).toLowerCase();
  return EXTENSION_TO_FORMAT[ext] || null;
}

export async function parseDocument(filePath: string, format?: DocumentFormat): Promise<ParsedDocument> {
  const detectedFormat = format || detectFormat(filePath);

  if (!detectedFormat) {
    throw new Error(`Unsupported file format: ${path.extname(filePath)}`);
  }

  switch (detectedFormat) {
    case 'txt':
      return parseTxt(filePath);
    case 'md':
      return parseMd(filePath);
    case 'html':
      return parseHtml(filePath);
    case 'pdf':
      return parsePdf(filePath);
    case 'epub':
      return parseEpub(filePath);
    default:
      throw new Error(`Unsupported format: ${detectedFormat}`);
  }
}

export { parseTxt, parseMd, parseHtml, parsePdf, parseEpub };

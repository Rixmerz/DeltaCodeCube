import fs from 'fs/promises';
import type { ParsedDocument } from '../types/index.js';

type PdfParseFunction = (buffer: Buffer) => Promise<{ text: string; numpages: number; info: Record<string, unknown> }>;

// Dynamic import for pdf-parse to handle ESM compatibility
let pdfParse: PdfParseFunction | null = null;

async function getPdfParser(): Promise<PdfParseFunction> {
  if (!pdfParse) {
    try {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const module = await import('pdf-parse');
      pdfParse = (module.default || module) as PdfParseFunction;
    } catch (error) {
      throw new Error('pdf-parse module not available. Install with: npm install pdf-parse');
    }
  }
  return pdfParse;
}

export async function parsePdf(filePath: string): Promise<ParsedDocument> {
  const parser = await getPdfParser();
  const buffer = await fs.readFile(filePath);
  const data = await parser(buffer);

  return {
    content: data.text,
    metadata: {
      pageCount: data.numpages,
      info: data.info,
      originalPath: filePath,
    },
  };
}

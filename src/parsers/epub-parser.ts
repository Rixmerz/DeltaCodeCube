import fs from 'fs/promises';
import path from 'path';
import * as cheerio from 'cheerio';
import type { ParsedDocument } from '../types/index.js';

// EPUB parser - EPUBs are ZIP files with XML/XHTML content
// For simplicity, we support unzipped EPUBs or fallback to text extraction

export async function parseEpub(filePath: string): Promise<ParsedDocument> {
  const absolutePath = path.resolve(filePath);

  // Check if it's a directory (unzipped EPUB)
  const stats = await fs.stat(absolutePath);

  if (stats.isDirectory()) {
    return parseUnzippedEpub(absolutePath);
  }

  // For zipped EPUB files, try to read and extract basic content
  // This is a simplified approach - production should use proper EPUB library
  try {
    const content = await fs.readFile(absolutePath, 'utf-8');

    // If it's readable as text, it might be an XHTML file
    if (content.includes('<?xml') || content.includes('<html')) {
      const $ = cheerio.load(content);
      $('script, style').remove();
      return {
        content: $('body').text().trim() || $.text().trim(),
        metadata: {
          originalPath: absolutePath,
          title: $('title').text() || undefined,
        },
      };
    }

    // Binary EPUB - return a message indicating need for manual extraction
    return {
      content: '',
      metadata: {
        originalPath: absolutePath,
        warning: 'EPUB file detected. For best results, unzip the EPUB first and provide the directory path.',
      },
    };
  } catch {
    throw new Error(`Failed to parse EPUB: ${absolutePath}. Try unzipping the EPUB first.`);
  }
}

async function parseUnzippedEpub(dirPath: string): Promise<ParsedDocument> {
  const contents: string[] = [];
  let title: string | undefined;

  // Try to find and parse content files
  const files = await findXhtmlFiles(dirPath);

  for (const file of files) {
    try {
      const content = await fs.readFile(file, 'utf-8');
      const $ = cheerio.load(content);
      $('script, style').remove();

      // Try to get title from first file
      if (!title) {
        title = $('title').text().trim() || undefined;
      }

      const text = $('body').text().trim();
      if (text) {
        contents.push(text);
      }
    } catch {
      // Skip problematic files
    }
  }

  return {
    content: contents.join('\n\n'),
    metadata: {
      title,
      originalPath: dirPath,
      fileCount: files.length,
    },
  };
}

async function findXhtmlFiles(dirPath: string): Promise<string[]> {
  const results: string[] = [];
  const entries = await fs.readdir(dirPath, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = path.join(dirPath, entry.name);
    if (entry.isDirectory()) {
      const subFiles = await findXhtmlFiles(fullPath);
      results.push(...subFiles);
    } else if (entry.name.endsWith('.xhtml') || entry.name.endsWith('.html') || entry.name.endsWith('.xml')) {
      // Skip metadata files
      if (!entry.name.includes('metadata') && !entry.name.includes('container')) {
        results.push(fullPath);
      }
    }
  }

  return results.sort();
}

import fs from 'fs/promises';
import * as cheerio from 'cheerio';
import type { ParsedDocument } from '../types/index.js';

export async function parseHtml(filePath: string): Promise<ParsedDocument> {
  const html = await fs.readFile(filePath, 'utf-8');
  const $ = cheerio.load(html);

  // Remove script and style elements
  $('script, style, noscript').remove();

  // Extract title
  const title = $('title').text().trim() || undefined;

  // Extract main content - prefer article, main, or body
  let contentElement = $('article').first();
  if (contentElement.length === 0) {
    contentElement = $('main').first();
  }
  if (contentElement.length === 0) {
    contentElement = $('body').first();
  }

  // Get text content, preserving some structure
  const content = contentElement
    .find('p, h1, h2, h3, h4, h5, h6, li, td, th, blockquote, pre')
    .map((_, el) => {
      const tag = el.tagName.toLowerCase();
      const text = $(el).text().trim();
      if (!text) return '';

      // Add markdown-like headers for structure detection
      if (tag.startsWith('h') && tag.length === 2) {
        const level = parseInt(tag[1]);
        return '#'.repeat(level) + ' ' + text;
      }
      return text;
    })
    .get()
    .filter(Boolean)
    .join('\n\n');

  return {
    content: content || $.text().trim(),
    metadata: {
      title,
      originalPath: filePath,
    },
  };
}

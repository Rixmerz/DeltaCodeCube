import fs from 'fs/promises';
import type { ParsedDocument } from '../types/index.js';

export async function parseMd(filePath: string): Promise<ParsedDocument> {
  const content = await fs.readFile(filePath, 'utf-8');

  // Extract any YAML frontmatter if present
  let metadata: Record<string, unknown> = {
    originalPath: filePath,
  };

  const frontmatterMatch = content.match(/^---\n([\s\S]*?)\n---\n/);
  if (frontmatterMatch) {
    // Simple YAML-like parsing for common keys
    const frontmatter = frontmatterMatch[1];
    const lines = frontmatter.split('\n');
    for (const line of lines) {
      const colonIndex = line.indexOf(':');
      if (colonIndex > 0) {
        const key = line.substring(0, colonIndex).trim();
        const value = line.substring(colonIndex + 1).trim().replace(/^["']|["']$/g, '');
        metadata[key] = value;
      }
    }
  }

  return {
    content,
    metadata,
  };
}

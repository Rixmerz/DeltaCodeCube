import { isStopWord } from './stopwords.js';

export interface TokenizeOptions {
  lowercase: boolean;
  removeStopWords: boolean;
  minLength: number;
  maxLength: number;
  stemming: boolean;
}

const DEFAULT_OPTIONS: TokenizeOptions = {
  lowercase: true,
  removeStopWords: true,
  minLength: 2,
  maxLength: 50,
  stemming: false,
};

/**
 * Tokenize text into words
 */
export function tokenize(text: string, options: Partial<TokenizeOptions> = {}): string[] {
  const opts = { ...DEFAULT_OPTIONS, ...options };

  // Normalize text
  let normalized = text;
  if (opts.lowercase) {
    normalized = normalized.toLowerCase();
  }

  // Remove punctuation except apostrophes in contractions
  normalized = normalized
    .replace(/[^\w\s'-]/g, ' ')
    .replace(/--+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  // Split into words
  let words = normalized.split(/\s+/).filter(word => word.length > 0);

  // Apply filters
  words = words.filter(word => {
    // Check length constraints
    if (word.length < opts.minLength || word.length > opts.maxLength) {
      return false;
    }

    // Check if it's a number only
    if (/^\d+$/.test(word)) {
      return false;
    }

    // Remove stop words if enabled
    if (opts.removeStopWords && isStopWord(word)) {
      return false;
    }

    return true;
  });

  // Apply basic stemming if enabled (simple suffix removal)
  if (opts.stemming) {
    words = words.map(word => simpleStem(word));
  }

  return words;
}

/**
 * Simple stemming - removes common suffixes
 * This is a basic implementation; for production use consider Porter/Snowball stemmer
 */
function simpleStem(word: string): string {
  // English suffixes
  const suffixes = ['ing', 'ed', 'es', 's', 'ment', 'ness', 'tion', 'ation', 'ly', 'er', 'est'];

  for (const suffix of suffixes) {
    if (word.endsWith(suffix) && word.length > suffix.length + 2) {
      return word.slice(0, -suffix.length);
    }
  }

  return word;
}

/**
 * Count term frequencies in text
 */
export function countTermFrequencies(text: string, options?: Partial<TokenizeOptions>): Map<string, number> {
  const tokens = tokenize(text, options);
  const frequencies = new Map<string, number>();

  for (const token of tokens) {
    frequencies.set(token, (frequencies.get(token) || 0) + 1);
  }

  return frequencies;
}

/**
 * Get top N terms by frequency
 */
export function getTopTerms(frequencies: Map<string, number>, n: number): Array<{ term: string; count: number }> {
  return Array.from(frequencies.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, n)
    .map(([term, count]) => ({ term, count }));
}

import Database from 'better-sqlite3';
import { Logger } from '../utils/logger.js';
import { ErrorHandler } from '../utils/errors.js';
import { getDocumentById } from '../db/queries/documents.js';
import { getSegmentsByDocumentId } from '../db/queries/segments.js';
import type { Segment } from '../types/index.js';

/**
 * Source Validation Module
 *
 * Prevents hallucinated grounding by detecting what the source document
 * actually contains vs. what external knowledge would be needed.
 */

export interface SourceCapabilities {
  documentId: number;
  documentTitle: string;
  detectedLanguages: string[];
  hasOriginalLanguages: boolean;  // Hebrew, Greek, Aramaic
  hasTranslationNotes: boolean;
  hasTextualVariants: boolean;
  hasCriticalApparatus: boolean;
  limitations: string[];
  warnings: string[];
}

// Language detection patterns
const LANGUAGE_PATTERNS = {
  hebrew: /[\u0590-\u05FF]/,
  greek: /[\u0370-\u03FF\u1F00-\u1FFF]/,
  aramaic: /[\u0700-\u074F]/,
  latin: /[a-zA-Z]/,
  transliteration: /\b(YHWH|Elohim|Adonai|Kyrios|Logos|Sophia|Ruach|Pneuma)\b/i,
};

// Patterns that indicate translation notes (not original text)
const TRANSLATION_NOTE_PATTERNS = [
  /\bLXX\b/,           // Septuagint reference
  /\bMT\b/,            // Masoretic Text reference
  /\bDSS\b/,           // Dead Sea Scrolls
  /\bHb\b/,            // Hebrew abbreviation
  /\bGk\b/,            // Greek abbreviation
  /\bLit\b/,           // Literal translation
  /\bOr\b/,            // Alternative translation
  /Other mss/,         // Manuscript variants
  /Some mss/,
];

export async function analyzeSourceCapabilities(
  db: Database.Database,
  documentId: number,
  logger: Logger
): Promise<SourceCapabilities> {
  const document = getDocumentById(db, documentId);
  if (!document) {
    throw new Error(`Document ${documentId} not found`);
  }

  const segments = getSegmentsByDocumentId(db, documentId);

  // Sample content for analysis (first 50 segments or all if less)
  const sampleSize = Math.min(50, segments.length);
  const sampleContent = segments
    .slice(0, sampleSize)
    .map((s: Segment) => s.content)
    .join(' ');

  const capabilities: SourceCapabilities = {
    documentId,
    documentTitle: document.title,
    detectedLanguages: [],
    hasOriginalLanguages: false,
    hasTranslationNotes: false,
    hasTextualVariants: false,
    hasCriticalApparatus: false,
    limitations: [],
    warnings: [],
  };

  // Detect languages present
  for (const [lang, pattern] of Object.entries(LANGUAGE_PATTERNS)) {
    if (pattern.test(sampleContent)) {
      capabilities.detectedLanguages.push(lang);
    }
  }

  // Check for original languages (actual characters, not transliterations)
  capabilities.hasOriginalLanguages =
    capabilities.detectedLanguages.includes('hebrew') ||
    capabilities.detectedLanguages.includes('greek') ||
    capabilities.detectedLanguages.includes('aramaic');

  // Check for translation notes
  for (const pattern of TRANSLATION_NOTE_PATTERNS) {
    if (pattern.test(sampleContent)) {
      capabilities.hasTranslationNotes = true;
      break;
    }
  }

  // Check for textual variants
  capabilities.hasTextualVariants =
    /Other mss|Some mss|LXX.*read|MT.*read/i.test(sampleContent);

  // Check for critical apparatus
  capabilities.hasCriticalApparatus =
    capabilities.hasTextualVariants &&
    /\bDSS\b|\bQumran\b|\bCodex\b|\bSinaiticus\b|\bVaticanus\b/i.test(sampleContent);

  // Generate limitations based on what's NOT present
  if (!capabilities.hasOriginalLanguages) {
    capabilities.limitations.push(
      'NO_ORIGINAL_LANGUAGES: Document does not contain Hebrew, Greek, or Aramaic text. ' +
      'Morphological and etymological analysis requires external sources.'
    );
  }

  if (!capabilities.hasTextualVariants) {
    capabilities.limitations.push(
      'NO_TEXTUAL_VARIANTS: Document does not contain manuscript variant information. ' +
      'Text-critical analysis requires external critical apparatus.'
    );
  }

  if (!capabilities.hasCriticalApparatus) {
    capabilities.limitations.push(
      'NO_CRITICAL_APPARATUS: Document lacks scholarly critical apparatus. ' +
      'Claims about manuscript traditions require external verification.'
    );
  }

  // Generate warnings for common hallucination traps
  if (capabilities.detectedLanguages.includes('transliteration') &&
      !capabilities.hasOriginalLanguages) {
    capabilities.warnings.push(
      'TRANSLITERATION_ONLY: Document contains transliterated terms (YHWH, Logos, etc.) ' +
      'but not original language text. Do not claim to analyze original morphology.'
    );
  }

  if (capabilities.hasTranslationNotes && !capabilities.hasCriticalApparatus) {
    capabilities.warnings.push(
      'TRANSLATION_NOTES_ONLY: Document has translation footnotes but lacks full critical apparatus. ' +
      'Variant readings are incomplete.'
    );
  }

  logger.info('Source capabilities analyzed', {
    documentId,
    languages: capabilities.detectedLanguages,
    hasOriginal: capabilities.hasOriginalLanguages,
    limitations: capabilities.limitations.length,
  });

  return capabilities;
}

/**
 * Validate that a claim can be grounded in the source document
 */
export interface ClaimValidation {
  claim: string;
  isGroundable: boolean;
  requiredCapabilities: string[];
  missingCapabilities: string[];
  recommendation: string;
}

export function validateClaim(
  claim: string,
  capabilities: SourceCapabilities
): ClaimValidation {
  const validation: ClaimValidation = {
    claim,
    isGroundable: true,
    requiredCapabilities: [],
    missingCapabilities: [],
    recommendation: '',
  };

  // Check if claim requires original languages
  const requiresOriginal =
    /\b(hebrew|greek|aramaic|morpholog|etymolog|root|stem|qal|hiphil|aorist|imperfect)\b/i.test(claim);

  if (requiresOriginal) {
    validation.requiredCapabilities.push('ORIGINAL_LANGUAGES');
    if (!capabilities.hasOriginalLanguages) {
      validation.missingCapabilities.push('ORIGINAL_LANGUAGES');
      validation.isGroundable = false;
    }
  }

  // Check if claim requires textual variants
  const requiresVariants =
    /\b(variant|manuscript|mss|textual criticism|masoretic|lxx|septuagint|codex)\b/i.test(claim);

  if (requiresVariants) {
    validation.requiredCapabilities.push('TEXTUAL_VARIANTS');
    if (!capabilities.hasTextualVariants) {
      validation.missingCapabilities.push('TEXTUAL_VARIANTS');
      validation.isGroundable = false;
    }
  }

  // Check if claim requires critical apparatus
  const requiresCritical =
    /\b(critical apparatus|dead sea|qumran|sinaiticus|vaticanus|alexandrinus)\b/i.test(claim);

  if (requiresCritical) {
    validation.requiredCapabilities.push('CRITICAL_APPARATUS');
    if (!capabilities.hasCriticalApparatus) {
      validation.missingCapabilities.push('CRITICAL_APPARATUS');
      validation.isGroundable = false;
    }
  }

  // Generate recommendation
  if (!validation.isGroundable) {
    validation.recommendation =
      `This claim requires ${validation.missingCapabilities.join(', ')} which the source document lacks. ` +
      `Either: (1) reformulate using only translation-level analysis, or ` +
      `(2) explicitly mark as requiring external sources.`;
  } else {
    validation.recommendation = 'Claim can be grounded in source document.';
  }

  return validation;
}

/**
 * Generate epistemological disclaimer for a document
 */
export function generateDisclaimer(capabilities: SourceCapabilities): string {
  const lines: string[] = [
    `## Source Document Limitations: "${capabilities.documentTitle}"`,
    '',
  ];

  if (capabilities.limitations.length > 0) {
    lines.push('### What this document CANNOT support:');
    for (const limitation of capabilities.limitations) {
      lines.push(`- ${limitation}`);
    }
    lines.push('');
  }

  if (capabilities.warnings.length > 0) {
    lines.push('### Warnings:');
    for (const warning of capabilities.warnings) {
      lines.push(`- ${warning}`);
    }
    lines.push('');
  }

  lines.push('### Detected capabilities:');
  lines.push(`- Languages: ${capabilities.detectedLanguages.join(', ') || 'English only'}`);
  lines.push(`- Has original language text: ${capabilities.hasOriginalLanguages ? 'Yes' : 'No'}`);
  lines.push(`- Has translation notes: ${capabilities.hasTranslationNotes ? 'Yes' : 'No'}`);
  lines.push(`- Has textual variants: ${capabilities.hasTextualVariants ? 'Yes' : 'No'}`);
  lines.push(`- Has critical apparatus: ${capabilities.hasCriticalApparatus ? 'Yes' : 'No'}`);

  return lines.join('\n');
}

import Database from 'better-sqlite3';
import { Logger } from '../utils/logger.js';

/**
 * Cognitive Constraints Module
 *
 * CORE PRINCIPLE: Tools deliver TEXT, agent must not produce MODEL.
 *
 * This module enforces strict boundaries on what cognitive operations
 * are permitted when working with document content.
 */

// ============================================================================
// PERMITTED OPERATIONS (WHITELIST)
// ============================================================================

export type PermittedOperation =
  | 'quote'           // Direct citation from document
  | 'list'            // Enumerate items found in document
  | 'paraphrase'      // Restate using ONLY document vocabulary
  | 'locate'          // Find where something appears
  | 'compare_verses'  // Compare A vs B within document
  | 'count'           // Count occurrences
  | 'extract';        // Pull specific data points

export type ProhibitedOperation =
  | 'synthesize'           // Combine concepts into new framework
  | 'explain_why'          // Infer divine/authorial intention
  | 'abstract'             // Create categories not in text
  | 'cross_section_infer'  // Draw conclusions across unconnected sections
  | 'causality_infer'      // Infer cause-effect not stated
  | 'teleology_infer';     // Infer purpose not stated

export interface OperationDeclaration {
  operationsUsed: PermittedOperation[];
  prohibitedAttempted: ProhibitedOperation[];
  isCompliant: boolean;
  violations: string[];
}

// ============================================================================
// INFERENTIAL CONNECTORS (BLOCKLIST)
// ============================================================================

/**
 * Connectors that signal unauthorized inference.
 * If output contains these, agent is likely synthesizing.
 */
const INFERENTIAL_CONNECTORS = [
  // English
  'therefore', 'thus', 'hence', 'consequently', 'accordingly',
  'implies', 'means that', 'shows that', 'indicates that',
  'suggests that', 'demonstrates that', 'proves that',
  'we can conclude', 'this means', 'in other words',
  'it follows that', 'as a result', 'for this reason',
  'this is why', 'because of this', 'leading to',
  // Spanish (for flexibility)
  'por lo tanto', 'por ende', 'en consecuencia', 'esto implica',
  'esto significa', 'esto demuestra', 'podemos concluir',
];

/**
 * Detect inferential connectors in output text.
 */
export function detectInferentialConnectors(text: string): {
  detected: boolean;
  connectors: string[];
  positions: { connector: string; index: number }[];
} {
  const lowerText = text.toLowerCase();
  const found: { connector: string; index: number }[] = [];

  for (const connector of INFERENTIAL_CONNECTORS) {
    const index = lowerText.indexOf(connector.toLowerCase());
    if (index !== -1) {
      found.push({ connector, index });
    }
  }

  return {
    detected: found.length > 0,
    connectors: found.map(f => f.connector),
    positions: found,
  };
}

// ============================================================================
// PROHIBITED ABSTRACT NOUNS (BLOCKLIST)
// ============================================================================

/**
 * Abstract nouns that signal unauthorized abstraction.
 * These are NOT in typical ancient texts but are philosophical imports.
 */
const PROHIBITED_ABSTRACTIONS = [
  // Philosophical/Theological
  'ontology', 'ontological', 'epistemology', 'epistemological',
  'metaphysics', 'metaphysical', 'phenomenology', 'phenomenological',
  'hermeneutics', 'hermeneutical', 'dialectic', 'dialectical',

  // Structural
  'mechanism', 'framework', 'structure', 'system', 'paradigm',
  'category', 'classification', 'taxonomy', 'typology',
  'architecture', 'infrastructure', 'superstructure',

  // Functional
  'function', 'functionality', 'operationalize', 'instantiate',
  'reify', 'hypostatize', 'systematize', 'conceptualize',

  // Modal/Causal
  'modality', 'causality', 'teleology', 'principle',
  'axiom', 'postulate', 'theorem', 'corollary',

  // Post-biblical theological
  'trinity', 'trinitarian', 'hypostasis', 'hypostatic',
  'consubstantial', 'homoousios', 'perichoresis',
  'procession', 'emanation', 'subsistence',
];

/**
 * Detect prohibited abstractions in output text.
 */
export function detectProhibitedAbstractions(text: string): {
  detected: boolean;
  terms: string[];
  severity: 'low' | 'medium' | 'high';
} {
  const lowerText = text.toLowerCase();
  const found: string[] = [];

  for (const term of PROHIBITED_ABSTRACTIONS) {
    if (lowerText.includes(term.toLowerCase())) {
      found.push(term);
    }
  }

  let severity: 'low' | 'medium' | 'high' = 'low';
  if (found.length >= 5) severity = 'high';
  else if (found.length >= 2) severity = 'medium';

  return {
    detected: found.length > 0,
    terms: found,
    severity,
  };
}

// ============================================================================
// VOCABULARY CONTROL
// ============================================================================

export interface VocabularyControl {
  documentId: number;
  allowedTokens: Set<string>;
  totalTokens: number;
  builtAt: Date;
}

/**
 * Build allowed vocabulary from document segments.
 * Only words actually in the document are permitted for paraphrase.
 */
export function buildDocumentVocabulary(
  db: Database.Database,
  documentId: number,
  logger: Logger
): VocabularyControl {
  const segments = db.prepare(`
    SELECT content FROM segments WHERE document_id = ?
  `).all(documentId) as { content: string }[];

  const allowedTokens = new Set<string>();

  for (const segment of segments) {
    // Tokenize: lowercase, remove punctuation, split on whitespace
    const tokens = segment.content
      .toLowerCase()
      .replace(/[^\w\s'-]/g, ' ')
      .split(/\s+/)
      .filter(t => t.length > 1);

    for (const token of tokens) {
      allowedTokens.add(token);
    }
  }

  logger.info('Vocabulary built', {
    documentId,
    totalTokens: allowedTokens.size,
  });

  return {
    documentId,
    allowedTokens,
    totalTokens: allowedTokens.size,
    builtAt: new Date(),
  };
}

/**
 * Check if output uses only allowed vocabulary.
 */
export function validateOutputVocabulary(
  output: string,
  vocabulary: VocabularyControl
): {
  isCompliant: boolean;
  illegalTokens: string[];
  complianceRate: number;
} {
  const outputTokens = output
    .toLowerCase()
    .replace(/[^\w\s'-]/g, ' ')
    .split(/\s+/)
    .filter(t => t.length > 1);

  const illegalTokens: string[] = [];

  for (const token of outputTokens) {
    if (!vocabulary.allowedTokens.has(token)) {
      // Check if it's a prohibited abstraction (worse)
      if (!PROHIBITED_ABSTRACTIONS.some(p => token.includes(p.toLowerCase()))) {
        illegalTokens.push(token);
      }
    }
  }

  const complianceRate = outputTokens.length > 0
    ? (outputTokens.length - illegalTokens.length) / outputTokens.length
    : 1;

  return {
    isCompliant: illegalTokens.length === 0,
    illegalTokens: [...new Set(illegalTokens)], // Dedupe
    complianceRate,
  };
}

// ============================================================================
// SCOPE CONTROL
// ============================================================================

export interface ScopeConstraints {
  maxSectionsPerResponse: number;
  maxBooksPerResponse: number;
  crossSectionSynthesisAllowed: boolean;
  requireExplicitConnection: boolean;
}

const DEFAULT_SCOPE: ScopeConstraints = {
  maxSectionsPerResponse: 3,
  maxBooksPerResponse: 2,
  crossSectionSynthesisAllowed: false,
  requireExplicitConnection: true,
};

export interface ScopeViolation {
  type: 'too_many_sections' | 'too_many_books' | 'unauthorized_synthesis' | 'missing_connection';
  details: string;
  sectionsUsed?: string[];
  booksUsed?: string[];
}

/**
 * Validate that response stays within scope constraints.
 */
export function validateScope(
  referencedSections: string[],
  referencedBooks: string[],
  containsSynthesis: boolean,
  hasExplicitConnection: boolean,
  constraints: ScopeConstraints = DEFAULT_SCOPE
): {
  isCompliant: boolean;
  violations: ScopeViolation[];
} {
  const violations: ScopeViolation[] = [];

  if (referencedSections.length > constraints.maxSectionsPerResponse) {
    violations.push({
      type: 'too_many_sections',
      details: `Referenced ${referencedSections.length} sections, max allowed is ${constraints.maxSectionsPerResponse}`,
      sectionsUsed: referencedSections,
    });
  }

  if (referencedBooks.length > constraints.maxBooksPerResponse) {
    violations.push({
      type: 'too_many_books',
      details: `Referenced ${referencedBooks.length} books, max allowed is ${constraints.maxBooksPerResponse}`,
      booksUsed: referencedBooks,
    });
  }

  if (containsSynthesis && !constraints.crossSectionSynthesisAllowed) {
    violations.push({
      type: 'unauthorized_synthesis',
      details: 'Cross-section synthesis detected but not authorized',
    });
  }

  if (referencedSections.length > 1 && constraints.requireExplicitConnection && !hasExplicitConnection) {
    violations.push({
      type: 'missing_connection',
      details: 'Multiple sections referenced without explicit textual connection',
    });
  }

  return {
    isCompliant: violations.length === 0,
    violations,
  };
}

// ============================================================================
// TEXT TYPE CLASSIFICATION
// ============================================================================

export type TextType =
  | 'narrative'      // Historical accounts, stories
  | 'poetry'         // Psalms, Song of Solomon
  | 'wisdom'         // Proverbs, Ecclesiastes, Job
  | 'prophecy'       // Isaiah, Jeremiah, etc.
  | 'epistle'        // Letters (NT)
  | 'apocalyptic'    // Daniel, Revelation
  | 'law'            // Leviticus, Deuteronomy
  | 'genealogy'      // Lists of descendants
  | 'unknown';

/**
 * Operations allowed per text type.
 * Different genres permit different cognitive operations.
 */
export const OPERATIONS_BY_TEXT_TYPE: Record<TextType, PermittedOperation[]> = {
  narrative: ['quote', 'list', 'paraphrase', 'locate', 'compare_verses', 'count', 'extract'],
  poetry: ['quote', 'list', 'locate', 'count'], // Paraphrase risky for poetry
  wisdom: ['quote', 'list', 'locate', 'compare_verses', 'count'],
  prophecy: ['quote', 'list', 'locate', 'count'], // Interpretation restricted
  epistle: ['quote', 'list', 'paraphrase', 'locate', 'compare_verses', 'count', 'extract'],
  apocalyptic: ['quote', 'list', 'locate', 'count'], // Heavily restricted
  law: ['quote', 'list', 'locate', 'count', 'extract'],
  genealogy: ['quote', 'list', 'locate', 'count', 'extract'],
  unknown: ['quote', 'list', 'locate', 'count'], // Conservative default
};

/**
 * Heuristic classification of text type based on content patterns.
 */
export function classifyTextType(content: string, title: string): TextType {
  const lowerContent = content.toLowerCase();
  const lowerTitle = title.toLowerCase();

  // Genealogy detection
  if (/\bson of\b.*\bson of\b.*\bson of\b/i.test(content) ||
      /\bbegat\b.*\bbegat\b/i.test(content) ||
      /\bfathered\b.*\bfathered\b.*\bfathered\b/i.test(content)) {
    return 'genealogy';
  }

  // Apocalyptic detection
  if (lowerTitle.includes('revelation') ||
      lowerTitle.includes('daniel') ||
      /\bvision\b.*\bsaw\b.*\bheaven\b/i.test(content) ||
      /\bseals?\b.*\btrumpets?\b.*\bbowls?\b/i.test(content)) {
    return 'apocalyptic';
  }

  // Poetry detection (Psalms structure)
  if (lowerTitle.includes('psalm') ||
      lowerTitle.includes('song of') ||
      /selah/i.test(content) ||
      content.split('\n').filter(l => l.trim().length > 0).length > 10 &&
      content.split('\n').every(l => l.length < 100)) {
    return 'poetry';
  }

  // Wisdom detection
  if (lowerTitle.includes('proverb') ||
      lowerTitle.includes('ecclesiastes') ||
      lowerTitle.includes('job') ||
      /\bwisdom\b.*\bunderstanding\b/i.test(content)) {
    return 'wisdom';
  }

  // Law detection
  if (lowerTitle.includes('leviticus') ||
      lowerTitle.includes('deuteronomy') ||
      /\bshall not\b.*\bshall not\b.*\bshall not\b/i.test(content) ||
      /\bcommandment\b/i.test(content)) {
    return 'law';
  }

  // Epistle detection
  if (/\bpaul\b.*\bto the\b/i.test(lowerTitle) ||
      /\bdear\b.*\bbrothers\b/i.test(content) ||
      /\bgrace\b.*\bpeace\b.*\bfrom\b/i.test(content)) {
    return 'epistle';
  }

  // Prophecy detection
  if (lowerTitle.includes('isaiah') ||
      lowerTitle.includes('jeremiah') ||
      lowerTitle.includes('ezekiel') ||
      /\bthus says the lord\b/i.test(content) ||
      /\bthe word of the lord came\b/i.test(content)) {
    return 'prophecy';
  }

  // Narrative detection (default for historical books)
  if (/\band\b.*\bsaid\b.*\band\b.*\bwent\b/i.test(content) ||
      /\bthen\b.*\bafter\b.*\bthen\b/i.test(content)) {
    return 'narrative';
  }

  return 'unknown';
}

// ============================================================================
// SAFE FALLBACK RESPONSE
// ============================================================================

export interface SafeFallback {
  triggered: boolean;
  reason: string;
  safeResponse: string;
}

/**
 * Generate safe fallback when question requires unauthorized operations.
 */
export function generateSafeFallback(
  questionType: 'synthesis' | 'explanation' | 'causality' | 'teleology' | 'cross_section',
  documentTitle: string
): SafeFallback {
  const fallbacks: Record<string, string> = {
    synthesis: `The document "${documentTitle}" does not synthesize these concepts explicitly. Only direct quotations are available.`,
    explanation: `The document "${documentTitle}" does not explain why this occurs. The text states what happens, not why.`,
    causality: `The document "${documentTitle}" does not state a causal relationship here. This would require inference beyond the text.`,
    teleology: `The document "${documentTitle}" does not state the purpose or intention. This would require interpretation.`,
    cross_section: `Cross-section analysis between these passages requires synthesis not present in the document. Each passage can only be quoted independently.`,
  };

  return {
    triggered: true,
    reason: `Question requires ${questionType} operation which is not permitted`,
    safeResponse: fallbacks[questionType] || `The document does not state this explicitly.`,
  };
}

// ============================================================================
// COMPLETE COGNITIVE AUDIT
// ============================================================================

export interface CognitiveAudit {
  timestamp: Date;
  documentId: number;
  queryAnalysis: {
    requiresSynthesis: boolean;
    requiresExplanation: boolean;
    requiresCausality: boolean;
    presupposesStructure: boolean;
  };
  outputAnalysis: {
    inferentialConnectors: ReturnType<typeof detectInferentialConnectors>;
    prohibitedAbstractions: ReturnType<typeof detectProhibitedAbstractions>;
    vocabularyCompliance?: ReturnType<typeof validateOutputVocabulary>;
  };
  scopeAnalysis?: ReturnType<typeof validateScope>;
  operationsUsed: PermittedOperation[];
  isCompliant: boolean;
  violations: string[];
  recommendation: 'proceed' | 'modify' | 'fallback';
  fallback?: SafeFallback;
}

/**
 * Analyze query for presupposed operations.
 */
export function analyzeQueryIntent(query: string): CognitiveAudit['queryAnalysis'] {
  const lowerQuery = query.toLowerCase();

  return {
    requiresSynthesis: /\b(how do|relationship between|connection|combine|unify|integrate)\b/i.test(lowerQuery),
    requiresExplanation: /\b(why|because|reason|explain|account for)\b/i.test(lowerQuery),
    requiresCausality: /\b(cause|effect|result|lead to|produce|make)\b/i.test(lowerQuery),
    presupposesStructure: /\b(structure|system|framework|pattern|architecture|mechanism)\b/i.test(lowerQuery),
  };
}

/**
 * Run complete cognitive audit on query + output.
 */
export function runCognitiveAudit(
  documentId: number,
  query: string,
  output: string,
  vocabulary?: VocabularyControl,
  referencedSections?: string[],
  referencedBooks?: string[],
  logger?: Logger
): CognitiveAudit {
  const queryAnalysis = analyzeQueryIntent(query);
  const inferentialConnectors = detectInferentialConnectors(output);
  const prohibitedAbstractions = detectProhibitedAbstractions(output);

  const violations: string[] = [];
  let recommendation: 'proceed' | 'modify' | 'fallback' = 'proceed';
  let fallback: SafeFallback | undefined;

  // Check query violations
  if (queryAnalysis.requiresSynthesis) {
    violations.push('Query requires synthesis (unauthorized)');
    recommendation = 'fallback';
    fallback = generateSafeFallback('synthesis', 'document');
  }

  if (queryAnalysis.requiresExplanation) {
    violations.push('Query requires explanation of "why" (unauthorized)');
    recommendation = 'fallback';
    fallback = generateSafeFallback('explanation', 'document');
  }

  // Check output violations
  if (inferentialConnectors.detected) {
    violations.push(`Inferential connectors detected: ${inferentialConnectors.connectors.join(', ')}`);
    recommendation = 'modify';
  }

  if (prohibitedAbstractions.detected) {
    violations.push(`Prohibited abstractions detected: ${prohibitedAbstractions.terms.join(', ')}`);
    if (prohibitedAbstractions.severity === 'high') {
      recommendation = 'fallback';
    } else {
      recommendation = 'modify';
    }
  }

  // Check vocabulary if provided
  let vocabularyCompliance: ReturnType<typeof validateOutputVocabulary> | undefined;
  if (vocabulary) {
    vocabularyCompliance = validateOutputVocabulary(output, vocabulary);
    if (!vocabularyCompliance.isCompliant && vocabularyCompliance.complianceRate < 0.8) {
      violations.push(`Vocabulary compliance ${(vocabularyCompliance.complianceRate * 100).toFixed(0)}% (threshold 80%)`);
      recommendation = 'modify';
    }
  }

  // Check scope if provided
  let scopeAnalysis: ReturnType<typeof validateScope> | undefined;
  if (referencedSections && referencedBooks) {
    scopeAnalysis = validateScope(
      referencedSections,
      referencedBooks,
      queryAnalysis.requiresSynthesis,
      false // Assume no explicit connection unless proven
    );
    if (!scopeAnalysis.isCompliant) {
      for (const v of scopeAnalysis.violations) {
        violations.push(v.details);
      }
      recommendation = 'fallback';
    }
  }

  const isCompliant = violations.length === 0;

  // Determine operations used (heuristic)
  const operationsUsed: PermittedOperation[] = [];
  if (/[""]/.test(output) || /\bquote\b/i.test(output)) operationsUsed.push('quote');
  if (/\d+\.\s|\-\s/.test(output)) operationsUsed.push('list');
  if (output.length > 100 && !operationsUsed.includes('quote')) operationsUsed.push('paraphrase');

  if (logger) {
    logger.info('Cognitive audit complete', {
      documentId,
      isCompliant,
      violationCount: violations.length,
      recommendation,
    });
  }

  return {
    timestamp: new Date(),
    documentId,
    queryAnalysis,
    outputAnalysis: {
      inferentialConnectors,
      prohibitedAbstractions,
      vocabularyCompliance,
    },
    scopeAnalysis,
    operationsUsed,
    isCompliant,
    violations,
    recommendation,
    fallback,
  };
}

// ============================================================================
// EXPORTS FOR TOOL REGISTRATION
// ============================================================================

export {
  INFERENTIAL_CONNECTORS,
  PROHIBITED_ABSTRACTIONS,
  DEFAULT_SCOPE,
};

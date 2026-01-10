import Database from 'better-sqlite3';
import { Logger } from '../utils/logger.js';

/**
 * Extraction Validators Module
 *
 * CORE PRINCIPLE: Validate that extracted content matches source EXACTLY.
 *
 * These tools prevent:
 * - Pattern completion hallucination (agent fills in expected patterns)
 * - Proximity violations (content from non-adjacent segments)
 * - Speaker misattribution (wrong agent attributed to speech)
 * - Schema overreach (adding commentary to pure data extraction)
 *
 * All tools are content-agnostic and work with any document type/language.
 */

// ============================================================================
// TYPES
// ============================================================================

export interface LiteralQuoteValidation {
  isValid: boolean;
  confidence: 'textual' | 'partial' | 'not_found';
  exactMatch: boolean;
  partialMatches: {
    matchedText: string;
    position: number;
    similarity: number;
  }[];
  suggestedCorrection?: string;
  segmentId?: number;
  errorDetails?: string;
}

export interface ProximityConstraint {
  baseSegmentId: number;
  maxDistance: number; // 0 = same segment, 1 = adjacent, etc.
  allowedSegmentIds: number[];
}

export interface ProximityValidation {
  isValid: boolean;
  baseSegmentId: number;
  targetSegmentId: number;
  distance: number;
  maxAllowed: number;
  violation?: string;
}

export interface SpeakerIdentification {
  speaker: string | null;
  confidence: 'explicit' | 'contextual' | 'ambiguous' | 'unknown';
  evidenceQuote: string | null;
  alternativeSpeakers: string[];
  isDirectSpeech: boolean;
  speechMarkers: string[];
}

export interface PatternContamination {
  detected: boolean;
  riskLevel: 'none' | 'low' | 'medium' | 'high';
  suspectedPatterns: {
    pattern: string;
    expectedCompletion: string;
    actualInText: boolean;
  }[];
  recommendation: string;
}

export interface ExtractionSchema {
  fields: {
    name: string;
    type: 'string' | 'number' | 'boolean' | 'array';
    required: boolean;
  }[];
  allowCommentary: boolean;
  requireConfidence: boolean;
}

export interface SchemaValidation {
  isValid: boolean;
  violations: {
    field: string;
    violation: 'missing' | 'wrong_type' | 'unauthorized_field' | 'contains_commentary';
    details: string;
  }[];
  cleanedOutput?: Record<string, unknown>;
}

// ============================================================================
// NEW: NARRATIVE VOICE ANALYSIS TYPES
// ============================================================================

/**
 * Narrative voice categories for text analysis.
 *
 * PRIMARY_NARRATION: Third-person narration of events as they happen
 *   - "The Lord said to Moses..."
 *   - "God created the heavens..."
 *   - "Fire came up from the rock..."
 *
 * DIVINE_DIRECT_SPEECH: First-person speech by a divine agent
 *   - "I am the Lord your God..."
 *   - "Let there be light..."
 *
 * HUMAN_TO_DIVINE: Human speech directed to God (prayer, praise, retrospective)
 *   - "You led them with a pillar of cloud..." (Nehemiah 9:12)
 *   - "O Lord, you are my God..."
 *
 * HUMAN_ABOUT_DIVINE: Human speech about God (not to God)
 *   - "The Lord is my shepherd..."
 *   - "Our God is a mighty God..."
 *
 * PROPHETIC_QUOTATION: Prophet quoting divine speech
 *   - "Thus says the Lord..."
 *   - "This is what the Lord declares..."
 */
export type NarrativeVoiceType =
  | 'primary_narration'
  | 'divine_direct_speech'
  | 'human_to_divine'
  | 'human_about_divine'
  | 'prophetic_quotation'
  | 'unknown';

export interface NarrativeVoiceAnalysis {
  voiceType: NarrativeVoiceType;
  confidence: 'high' | 'medium' | 'low';
  indicators: string[];
  /**
   * Who is performing the speech act (the one speaking/writing)
   */
  discursiveAgent: string | null;
  /**
   * Who is being addressed (if applicable)
   */
  addressee: string | null;
  /**
   * Is the divine action executed in-scene or merely referenced?
   */
  actionExecutionMode: 'in_scene' | 'retrospective' | 'prospective' | 'hypothetical' | 'none';
  /**
   * Warning if the voice type may cause confusion in extraction
   */
  warning?: string;
}

// ============================================================================
// NEW: AGENCY EXECUTION TYPES
// ============================================================================

/**
 * Distinguishes between action executed in the narrative present
 * vs action merely described, recalled, or anticipated.
 */
export type AgencyMode =
  | 'executed'      // Action happens NOW in the narrative
  | 'retrospective' // Action recalled from past
  | 'prospective'   // Action prophesied/anticipated
  | 'hypothetical'  // Action described conditionally
  | 'referenced';   // Action mentioned but not performed in this text unit

export interface AgencyValidation {
  isExecuted: boolean;
  mode: AgencyMode;
  agent: string | null;
  action: string | null;
  verbTense: 'past' | 'present' | 'future' | 'imperative' | 'mixed' | 'unknown';
  evidenceQuotes: string[];
  /**
   * If retrospective, who is doing the recalling?
   */
  retrospectiveNarrator?: string;
  warning?: string;
}

// ============================================================================
// NEW: QUANTIFIER VALIDATION TYPES
// ============================================================================

export interface WeakQuantifier {
  term: string;
  position: number;
  context: string;
  requiresEvidence: boolean;
}

export interface QuantifierValidation {
  hasWeakQuantifiers: boolean;
  quantifiers: WeakQuantifier[];
  recommendation: 'block' | 'require_count' | 'allow';
  suggestedReplacement?: string;
}

// ============================================================================
// NEW: EXISTENTIAL RESPONSE VALIDATION TYPES
// ============================================================================

/**
 * For closed existential questions ("Does X exist in the text?"),
 * only two valid response types are allowed:
 *
 * 1. AFFIRMED: "YES" + at least one concrete textual evidence
 * 2. DENIED: "NO" + explicit statement of non-existence
 *
 * Any meta-discourse, hedging, or evasion is INVALID.
 */
export type ExistentialResponseType =
  | 'affirmed'    // YES + evidence
  | 'denied'      // NO + explicit denial
  | 'evaded'      // Invalid: hedged, meta-discourse, or incomplete
  | 'malformed';  // Invalid: couldn't parse response

export interface ExistentialEvidence {
  quote: string;
  location?: string;
  verified: boolean;
}

export interface ExistentialResponseValidation {
  isValid: boolean;
  responseType: ExistentialResponseType;
  /**
   * For 'affirmed' responses: the evidence provided
   */
  evidence: ExistentialEvidence[];
  /**
   * Evasion patterns detected (if any)
   */
  evasionPatterns: EvasionPattern[];
  /**
   * If invalid, what's wrong
   */
  violations: string[];
  /**
   * Corrective action required
   */
  requiredAction: 'none' | 'provide_evidence' | 'state_no_explicitly' | 'remove_meta_discourse' | 'retry';
}

export interface EvasionPattern {
  type: 'limitation_excuse' | 'meta_discourse' | 'unnecessary_question' | 'category_introduction' | 'hedging' | 'probability_without_evidence';
  matchedText: string;
  severity: 'warning' | 'violation';
}

// ============================================================================
// 1. LITERAL QUOTE VALIDATOR
// ============================================================================

/**
 * Validates that a quoted string exists EXACTLY in the specified segment/document.
 *
 * Use case: Agent claims "And it was so" appears in Genesis 1:28 - verify it actually does.
 *
 * @param db Database connection
 * @param quote The quoted text to validate
 * @param segmentId Optional: specific segment to check
 * @param documentId Optional: document to search (if no segmentId)
 * @param fuzzyThreshold Similarity threshold for partial matches (0-1, default 0.8)
 */
export function validateLiteralQuote(
  db: Database.Database,
  quote: string,
  segmentId?: number,
  documentId?: number,
  fuzzyThreshold: number = 0.8,
  logger?: Logger
): LiteralQuoteValidation {
  if (!quote || quote.trim().length === 0) {
    return {
      isValid: false,
      confidence: 'not_found',
      exactMatch: false,
      partialMatches: [],
      errorDetails: 'Empty quote provided',
    };
  }

  const normalizedQuote = normalizeText(quote);
  let segments: { id: number; content: string }[];

  // Fetch segments to search
  if (segmentId) {
    const segment = db.prepare(`
      SELECT id, content FROM segments WHERE id = ?
    `).get(segmentId) as { id: number; content: string } | undefined;

    if (!segment) {
      return {
        isValid: false,
        confidence: 'not_found',
        exactMatch: false,
        partialMatches: [],
        errorDetails: `Segment ${segmentId} not found`,
      };
    }
    segments = [segment];
  } else if (documentId) {
    segments = db.prepare(`
      SELECT id, content FROM segments WHERE document_id = ?
    `).all(documentId) as { id: number; content: string }[];
  } else {
    return {
      isValid: false,
      confidence: 'not_found',
      exactMatch: false,
      partialMatches: [],
      errorDetails: 'Must provide either segmentId or documentId',
    };
  }

  // Search for exact match first
  for (const segment of segments) {
    const normalizedContent = normalizeText(segment.content);

    // Exact match check
    if (normalizedContent.includes(normalizedQuote)) {
      const position = normalizedContent.indexOf(normalizedQuote);
      logger?.info('Literal quote validated', { segmentId: segment.id, exactMatch: true });

      return {
        isValid: true,
        confidence: 'textual',
        exactMatch: true,
        partialMatches: [{
          matchedText: quote,
          position,
          similarity: 1.0,
        }],
        segmentId: segment.id,
      };
    }
  }

  // Fuzzy match search
  const partialMatches: LiteralQuoteValidation['partialMatches'] = [];

  for (const segment of segments) {
    const similarity = calculateSimilarity(normalizedQuote, normalizeText(segment.content));

    if (similarity >= fuzzyThreshold) {
      // Find best matching substring
      const bestMatch = findBestSubstringMatch(normalizedQuote, segment.content);
      if (bestMatch) {
        partialMatches.push({
          matchedText: bestMatch.text,
          position: bestMatch.position,
          similarity: bestMatch.similarity,
        });
      }
    }
  }

  // Sort by similarity descending
  partialMatches.sort((a, b) => b.similarity - a.similarity);

  if (partialMatches.length > 0 && partialMatches[0].similarity >= fuzzyThreshold) {
    logger?.info('Literal quote partial match', {
      similarity: partialMatches[0].similarity,
      suggested: partialMatches[0].matchedText,
    });

    return {
      isValid: false,
      confidence: 'partial',
      exactMatch: false,
      partialMatches: partialMatches.slice(0, 3), // Top 3 matches
      suggestedCorrection: partialMatches[0].matchedText,
      errorDetails: `Exact quote not found. Did you mean: "${partialMatches[0].matchedText}"?`,
    };
  }

  logger?.warn('Literal quote not found', { quote: quote.substring(0, 50) });

  return {
    isValid: false,
    confidence: 'not_found',
    exactMatch: false,
    partialMatches: partialMatches.slice(0, 3),
    errorDetails: 'Quote not found in specified segment(s)',
  };
}

// ============================================================================
// 2. PROXIMITY CONSTRAINT EXTRACTOR
// ============================================================================

/**
 * Validates that content is extracted from adjacent segments only.
 *
 * Use case: Effect must be in same verse or verse+1, not 5 verses later.
 *
 * @param db Database connection
 * @param baseSegmentId The anchor segment (e.g., where God speaks)
 * @param targetSegmentId The segment being referenced for effect
 * @param maxDistance Maximum allowed segment distance (0 = same, 1 = adjacent)
 */
export function validateProximity(
  db: Database.Database,
  baseSegmentId: number,
  targetSegmentId: number,
  maxDistance: number = 1,
  logger?: Logger
): ProximityValidation {
  // Get segment positions
  const segments = db.prepare(`
    SELECT id, position, document_id FROM segments
    WHERE id IN (?, ?)
  `).all(baseSegmentId, targetSegmentId) as { id: number; position: number; document_id: number }[];

  if (segments.length !== 2) {
    return {
      isValid: false,
      baseSegmentId,
      targetSegmentId,
      distance: -1,
      maxAllowed: maxDistance,
      violation: 'One or both segments not found',
    };
  }

  const base = segments.find(s => s.id === baseSegmentId)!;
  const target = segments.find(s => s.id === targetSegmentId)!;

  // Must be in same document
  if (base.document_id !== target.document_id) {
    return {
      isValid: false,
      baseSegmentId,
      targetSegmentId,
      distance: -1,
      maxAllowed: maxDistance,
      violation: 'Segments are from different documents',
    };
  }

  const distance = Math.abs(target.position - base.position);

  logger?.info('Proximity check', { baseSegmentId, targetSegmentId, distance, maxDistance });

  if (distance > maxDistance) {
    return {
      isValid: false,
      baseSegmentId,
      targetSegmentId,
      distance,
      maxAllowed: maxDistance,
      violation: `Distance ${distance} exceeds maximum ${maxDistance}`,
    };
  }

  return {
    isValid: true,
    baseSegmentId,
    targetSegmentId,
    distance,
    maxAllowed: maxDistance,
  };
}

/**
 * Get list of segment IDs within proximity constraint.
 */
export function getAdjacentSegmentIds(
  db: Database.Database,
  baseSegmentId: number,
  maxDistance: number = 1,
  logger?: Logger
): number[] {
  const baseSegment = db.prepare(`
    SELECT document_id, position FROM segments WHERE id = ?
  `).get(baseSegmentId) as { document_id: number; position: number } | undefined;

  if (!baseSegment) {
    logger?.warn('Base segment not found', { baseSegmentId });
    return [];
  }

  const minPos = baseSegment.position - maxDistance;
  const maxPos = baseSegment.position + maxDistance;

  const adjacent = db.prepare(`
    SELECT id FROM segments
    WHERE document_id = ? AND position BETWEEN ? AND ?
    ORDER BY position
  `).all(baseSegment.document_id, minPos, maxPos) as { id: number }[];

  return adjacent.map(s => s.id);
}

// ============================================================================
// 3. SPEAKER IDENTIFICATION
// ============================================================================

// Speech introduction patterns (multilingual) - GENERIC
const SPEECH_MARKERS = {
  english: [
    /(\w+)\s+said/i,
    /(\w+)\s+spoke/i,
    /(\w+)\s+answered/i,
    /(\w+)\s+replied/i,
    /(\w+)\s+asked/i,
    /(\w+)\s+declared/i,
    /(\w+)\s+commanded/i,
    /(\w+)\s+cried/i,
    /(\w+)\s+called/i,
    /said\s+(\w+)/i,
    /says?\s+the\s+(\w+)/i,
    /the\s+(\w+)\s+said/i,
  ],
  spanish: [
    /(\w+)\s+dijo/i,
    /(\w+)\s+habló/i,
    /(\w+)\s+respondió/i,
    /(\w+)\s+preguntó/i,
    /(\w+)\s+declaró/i,
    /(\w+)\s+mandó/i,
    /dijo\s+(\w+)/i,
    /dice\s+el\s+(\w+)/i,
  ],
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Convert a string term to a case-insensitive RegExp with word boundaries.
 * @internal
 */
function createPatternRegExp(term: string): RegExp {
  // Escape special regex characters
  const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  // Create pattern with word boundaries for exact matching
  return new RegExp(`\\b${escaped}\\b`, 'i');
}

// ============================================================================
// INTERFACES
// ============================================================================

export interface SpeakerIdentificationOptions {
  /**
   * Speaker names to prioritize when multiple speakers found.
   * Agent constructs dynamically based on document context.
   * Examples:
   * - Religious texts: ['God', 'Lord', 'Allah']
   * - Academic papers: ['Dr. Smith', 'Professor Jones']
   * - Legal documents: ['Plaintiff', 'Defendant']
   * - Fairy tales: ['King', 'Queen', 'Prince']
   */
  priorityPatterns?: string[];

  /**
   * Speaker patterns to flag as ambiguous/problematic.
   * Agent constructs dynamically based on context.
   * Examples:
   * - Religious texts: ['angel of', 'messenger', 'prophet']
   * - Academic papers: ['assistant', 'student']
   */
  excludePatterns?: string[];
}

/**
 * Identifies the speaker of quoted speech in a text segment.
 *
 * GENERIC by default. For context-specific behavior, pass options:
 * - priorityPatterns: Speakers to prioritize (e.g., BIBLICAL_SPEAKER_PRIORITY)
 * - excludePatterns: Speakers to flag as ambiguous (e.g., BIBLICAL_SPEAKER_EXCLUDE)
 *
 * @param content The text content to analyze
 * @param targetSpeaker Optional: verify this specific speaker
 * @param logger Optional logger
 * @param options Optional configuration for priority/exclude patterns
 */
export function identifySpeaker(
  content: string,
  targetSpeaker?: string,
  logger?: Logger,
  options?: SpeakerIdentificationOptions
): SpeakerIdentification {
  const foundSpeakers: string[] = [];
  const speechMarkers: string[] = [];

  // Search for speech markers in all supported languages
  for (const [lang, patterns] of Object.entries(SPEECH_MARKERS)) {
    for (const pattern of patterns) {
      const match = content.match(pattern);
      if (match) {
        const speaker = match[1];
        if (speaker && !foundSpeakers.includes(speaker)) {
          foundSpeakers.push(speaker);
          speechMarkers.push(match[0]);
        }
      }
    }
  }

  // Check if direct speech is present (quotes)
  const hasDirectSpeech = /"[^"]{5,}"/.test(content) ||
                          /«[^»]{5,}»/.test(content) ||
                          /"[^"]{5,}"/.test(content);

  // Determine confidence level
  let confidence: SpeakerIdentification['confidence'] = 'unknown';
  let primarySpeaker: string | null = null;
  let evidenceQuote: string | null = null;

  if (foundSpeakers.length === 1) {
    primarySpeaker = foundSpeakers[0];
    confidence = 'explicit';
    evidenceQuote = speechMarkers[0];
  } else if (foundSpeakers.length > 1) {
    // Multiple speakers - check for priority patterns (if provided)
    if (options?.priorityPatterns && options.priorityPatterns.length > 0) {
      const priorityFound = foundSpeakers.find(s =>
        options.priorityPatterns!.some(term => createPatternRegExp(term).test(s))
      );
      if (priorityFound) {
        primarySpeaker = priorityFound;
        confidence = 'contextual';
        evidenceQuote = speechMarkers[foundSpeakers.indexOf(priorityFound)];
      } else {
        primarySpeaker = foundSpeakers[0]; // First mentioned
        confidence = 'ambiguous';
        evidenceQuote = speechMarkers[0];
      }
    } else {
      // No priority patterns - use first mentioned speaker
      primarySpeaker = foundSpeakers[0];
      confidence = 'ambiguous'; // Ambiguous since multiple speakers and no priority
      evidenceQuote = speechMarkers[0];
    }
  }

  // Check for exclude patterns (if provided)
  if (options?.excludePatterns && options.excludePatterns.length > 0) {
    const hasExcludedPattern = options.excludePatterns.some(term =>
      createPatternRegExp(term).test(content)
    );
    if (hasExcludedPattern) {
      logger?.info('Excluded pattern detected in content', {
        patterns: options.excludePatterns,
      });
      return {
        speaker: primarySpeaker,
        confidence: 'ambiguous', // Downgrade confidence
        evidenceQuote,
        alternativeSpeakers: foundSpeakers.filter(s => s !== primarySpeaker),
        isDirectSpeech: hasDirectSpeech,
        speechMarkers,
      };
    }
  }

  logger?.info('Speaker identified', {
    speaker: primarySpeaker,
    confidence,
    alternatives: foundSpeakers.length - 1,
  });

  return {
    speaker: primarySpeaker,
    confidence,
    evidenceQuote,
    alternativeSpeakers: foundSpeakers.filter(s => s !== primarySpeaker),
    isDirectSpeech: hasDirectSpeech,
    speechMarkers,
  };
}

/**
 * Validates that a specific speaker is the agent in a segment.
 */
export function validateSpeaker(
  db: Database.Database,
  segmentId: number,
  expectedSpeaker: string,
  logger?: Logger,
  options?: SpeakerIdentificationOptions
): {
  isValid: boolean;
  actualSpeaker: string | null;
  confidence: SpeakerIdentification['confidence'];
  details: string;
} {
  const segment = db.prepare(`
    SELECT content FROM segments WHERE id = ?
  `).get(segmentId) as { content: string } | undefined;

  if (!segment) {
    return {
      isValid: false,
      actualSpeaker: null,
      confidence: 'unknown',
      details: `Segment ${segmentId} not found`,
    };
  }

  const identification = identifySpeaker(segment.content, expectedSpeaker, logger, options);

  // Normalize for comparison
  const expectedLower = expectedSpeaker.toLowerCase();
  const actualLower = identification.speaker?.toLowerCase() || '';

  // Check if expected matches actual
  let isMatch = actualLower === expectedLower;

  // If priority patterns provided, check if both expected and actual match same priority group
  if (!isMatch && options?.priorityPatterns && options.priorityPatterns.length > 0) {
    const matchesPriorityExpected = options.priorityPatterns.some(term =>
      createPatternRegExp(term).test(expectedSpeaker)
    );
    const matchesPriorityActual = identification.speaker !== null &&
      options.priorityPatterns.some(term =>
        createPatternRegExp(term).test(identification.speaker as string)
      );

    isMatch = matchesPriorityExpected && matchesPriorityActual;
  }

  return {
    isValid: Boolean(isMatch) && identification.confidence !== 'ambiguous',
    actualSpeaker: identification.speaker,
    confidence: identification.confidence,
    details: isMatch
      ? `Speaker "${identification.speaker}" matches expected "${expectedSpeaker}"`
      : `Expected "${expectedSpeaker}" but found "${identification.speaker || 'unknown'}"`,
  };
}

// ============================================================================
// 4. PATTERN CONTAMINATION DETECTOR
// ============================================================================

/**
 * Pattern definition for contamination detection.
 * Agent constructs these dynamically based on document genre.
 */
export interface PatternDefinition {
  /**
   * Trigger phrase (as string, will be converted to case-insensitive RegExp).
   * Examples:
   * - "and God said"
   * - "once upon a time"
   * - "whereas the party"
   */
  trigger: string;

  /**
   * Expected completion phrase that agent might hallucinate.
   * Examples:
   * - "and it was so"
   * - "happily ever after"
   * - "hereby agrees"
   */
  expectedCompletion: string;

  /**
   * Optional description of the pattern.
   */
  description?: string;
}

/**
 * Detects when agent output may be completing a pattern not in source.
 *
 * GENERIC by default (no patterns). Agent provides patterns dynamically:
 * - Biblical: {trigger: "and God said", expectedCompletion: "and it was so"}
 * - Fairy tale: {trigger: "once upon a time", expectedCompletion: "happily ever after"}
 * - Legal: {trigger: "whereas", expectedCompletion: "hereby agrees"}
 *
 * @param claimedOutput What the agent claims is in the text
 * @param actualSource The actual source text content
 * @param logger Optional logger
 * @param patterns Optional pattern definitions (empty array = no specific detection)
 */
export function detectPatternContamination(
  claimedOutput: string,
  actualSource: string,
  logger?: Logger,
  patterns?: PatternDefinition[]
): PatternContamination {
  const suspectedPatterns: PatternContamination['suspectedPatterns'] = [];
  let riskLevel: PatternContamination['riskLevel'] = 'none';

  const normalizedOutput = normalizeText(claimedOutput);
  const normalizedSource = normalizeText(actualSource);

  // Only check patterns if provided
  const patternsToCheck = patterns || [];

  for (const patternDef of patternsToCheck) {
    // Convert trigger string to RegExp (case-insensitive)
    const triggerRegExp = new RegExp(patternDef.trigger, 'i');

    // Check if trigger pattern exists in source
    const triggerInSource = triggerRegExp.test(actualSource);
    const completionInOutput = normalizedOutput.includes(
      normalizeText(patternDef.expectedCompletion)
    );
    const completionInSource = normalizedSource.includes(
      normalizeText(patternDef.expectedCompletion)
    );

    // Risk: Trigger in source, completion in output, but completion NOT in source
    if (triggerInSource && completionInOutput && !completionInSource) {
      suspectedPatterns.push({
        pattern: patternDef.description || `Pattern: ${patternDef.trigger}`,
        expectedCompletion: patternDef.expectedCompletion,
        actualInText: false,
      });
    }
  }

  // Calculate risk level
  if (suspectedPatterns.length === 0) {
    riskLevel = 'none';
  } else if (suspectedPatterns.length === 1) {
    riskLevel = 'medium';
  } else {
    riskLevel = 'high';
  }

  let recommendation = 'Output appears clean of pattern contamination.';
  if (riskLevel !== 'none') {
    recommendation = `VERIFY: ${suspectedPatterns.length} potential pattern completion(s) detected. ` +
      `Agent may have added "${suspectedPatterns[0].expectedCompletion}" which is NOT in source text.`;
  }

  logger?.info('Pattern contamination check', {
    riskLevel,
    patternsDetected: suspectedPatterns.length,
  });

  return {
    detected: suspectedPatterns.length > 0,
    riskLevel,
    suspectedPatterns,
    recommendation,
  };
}

// ============================================================================
// 5. STRICT EXTRACTION SCHEMA VALIDATOR
// ============================================================================

// Patterns that indicate commentary (not pure extraction)
const COMMENTARY_INDICATORS = [
  /\(.*?\)/,                           // Parenthetical comments
  /note[s]?:/i,                        // Notes sections
  /importantly/i,                      // Evaluative language
  /interestingly/i,
  /significantly/i,
  /it is worth noting/i,
  /this shows/i,
  /this demonstrates/i,
  /this means/i,
  /this indicates/i,
  /in other words/i,
  /immediate.*follows/i,              // Agent adding interpretation
  /clearly/i,
  /obviously/i,
  /certainly/i,
  /definitely/i,
  /perhaps/i,                          // Speculation
  /possibly/i,
  /maybe/i,
  /seems to/i,
  /appears to/i,
  /limitations?:/i,                    // Meta-commentary
  /caveat/i,
];

/**
 * Validates that extraction output follows a strict schema without commentary.
 *
 * Use case: User asks for "Book | Chapter:Verse | speech | effect"
 * Agent should return ONLY that, no parentheticals, no notes.
 *
 * @param output The agent's output to validate
 * @param schema The expected output schema
 */
export function validateExtractionSchema(
  output: string,
  schema: ExtractionSchema,
  logger?: Logger
): SchemaValidation {
  const violations: SchemaValidation['violations'] = [];

  // Check for unauthorized commentary
  if (!schema.allowCommentary) {
    for (const pattern of COMMENTARY_INDICATORS) {
      if (pattern.test(output)) {
        const match = output.match(pattern);
        violations.push({
          field: '_commentary',
          violation: 'contains_commentary',
          details: `Found unauthorized commentary: "${match?.[0]}"`,
        });
      }
    }
  }

  // Try to parse as structured data (table format, JSON, etc.)
  const parsedRows = parseTableOutput(output);

  // Validate each expected field
  for (const field of schema.fields) {
    if (field.required) {
      // Check if field appears in output
      const fieldRegex = new RegExp(`\\b${field.name}\\b`, 'i');
      const hasField = parsedRows.some(row =>
        Object.keys(row).some(k => fieldRegex.test(k) || row[k] !== undefined)
      );

      if (!hasField && parsedRows.length === 0) {
        // Can't determine field presence in unstructured output
        // Don't flag as missing if output exists
      }
    }
  }

  // Check for unauthorized fields (fields not in schema)
  if (parsedRows.length > 0) {
    const allowedFields = new Set(schema.fields.map(f => f.name.toLowerCase()));
    for (const row of parsedRows) {
      for (const key of Object.keys(row)) {
        const normalizedKey = key.toLowerCase().replace(/[^a-z]/g, '');
        if (!allowedFields.has(normalizedKey) &&
            !schema.fields.some(f => f.name.toLowerCase().includes(normalizedKey))) {
          violations.push({
            field: key,
            violation: 'unauthorized_field',
            details: `Field "${key}" not in schema`,
          });
        }
      }
    }
  }

  logger?.info('Schema validation', {
    isValid: violations.length === 0,
    violationCount: violations.length,
  });

  return {
    isValid: violations.length === 0,
    violations,
    cleanedOutput: violations.length > 0 ? cleanOutput(output, schema) : undefined,
  };
}

/**
 * Creates a strict schema for extraction.
 */
export function createExtractionSchema(
  fields: string[],
  options: {
    allowCommentary?: boolean;
    requireConfidence?: boolean;
  } = {}
): ExtractionSchema {
  return {
    fields: fields.map(name => ({
      name,
      type: 'string',
      required: true,
    })),
    allowCommentary: options.allowCommentary ?? false,
    requireConfidence: options.requireConfidence ?? true,
  };
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Normalize text for comparison (lowercase, collapse whitespace, remove punctuation).
 */
function normalizeText(text: string): string {
  return text
    .toLowerCase()
    .replace(/[""''«»]/g, '"')
    .replace(/[\n\r\t]+/g, ' ')
    .replace(/\s+/g, ' ')
    .replace(/[^\w\s"'-]/g, '')
    .trim();
}

/**
 * Calculate similarity between two strings using Levenshtein-based approach.
 */
function calculateSimilarity(a: string, b: string): number {
  // Use Jaccard similarity for efficiency with long texts
  const wordsA = new Set(a.split(/\s+/));
  const wordsB = new Set(b.split(/\s+/));

  const intersection = new Set([...wordsA].filter(w => wordsB.has(w)));
  const union = new Set([...wordsA, ...wordsB]);

  return intersection.size / union.size;
}

/**
 * Find the best matching substring in content for a given query.
 */
function findBestSubstringMatch(
  query: string,
  content: string
): { text: string; position: number; similarity: number } | null {
  const queryWords = query.split(/\s+/);
  const contentWords = content.split(/\s+/);

  if (queryWords.length > contentWords.length) return null;

  let bestMatch: { text: string; position: number; similarity: number } | null = null;

  // Sliding window
  for (let i = 0; i <= contentWords.length - queryWords.length; i++) {
    const window = contentWords.slice(i, i + queryWords.length + 2); // +2 for flexibility
    const windowText = window.join(' ');

    const similarity = calculateSimilarity(
      normalizeText(query),
      normalizeText(windowText)
    );

    if (!bestMatch || similarity > bestMatch.similarity) {
      bestMatch = {
        text: windowText,
        position: i,
        similarity,
      };
    }
  }

  return bestMatch;
}

/**
 * Parse table-like output into structured rows.
 */
function parseTableOutput(output: string): Record<string, string>[] {
  const rows: Record<string, string>[] = [];
  const lines = output.split('\n').filter(l => l.trim());

  // Detect delimiter (| or tabs or commas)
  const firstLine = lines[0] || '';
  let delimiter = '|';
  if (firstLine.includes('\t')) delimiter = '\t';
  else if (firstLine.includes(',') && !firstLine.includes('|')) delimiter = ',';

  // Try to find header row
  let headerIndex = -1;
  for (let i = 0; i < Math.min(3, lines.length); i++) {
    if (lines[i].split(delimiter).length >= 2) {
      headerIndex = i;
      break;
    }
  }

  if (headerIndex === -1) return rows;

  const headers = lines[headerIndex]
    .split(delimiter)
    .map(h => h.trim().toLowerCase().replace(/[^a-z]/g, ''));

  // Parse data rows
  for (let i = headerIndex + 1; i < lines.length; i++) {
    const line = lines[i];
    if (line.startsWith('---') || line.startsWith('===')) continue; // Skip separators

    const values = line.split(delimiter).map(v => v.trim());
    if (values.length >= headers.length - 1) {
      const row: Record<string, string> = {};
      headers.forEach((h, idx) => {
        if (h && values[idx]) row[h] = values[idx];
      });
      if (Object.keys(row).length > 0) rows.push(row);
    }
  }

  return rows;
}

/**
 * Remove commentary from output based on schema.
 */
function cleanOutput(
  output: string,
  schema: ExtractionSchema
): Record<string, unknown> {
  // Remove parentheticals
  let cleaned = output.replace(/\([^)]*\)/g, '');

  // Remove notes sections
  cleaned = cleaned.replace(/note[s]?:.*$/gim, '');

  // Remove lines with evaluative language
  const lines = cleaned.split('\n').filter(line => {
    const lower = line.toLowerCase();
    return !COMMENTARY_INDICATORS.some(p => p.test(line));
  });

  return {
    originalLength: output.length,
    cleanedLength: lines.join('\n').length,
    linesRemoved: output.split('\n').length - lines.length,
    cleanedText: lines.join('\n'),
  };
}

// ============================================================================
// 7. NARRATIVE VOICE DETECTOR
// ============================================================================
/**
 * STRUCTURAL patterns for narrative voice detection (PURE - no vocabulary).
 * These detect voice type based ONLY on grammatical structure.
 * All vocabulary (agents, verbs, etc.) must be provided by the agent via DomainVocabulary.
 */
const STRUCTURAL_NARRATIVE_VOICE_PATTERNS = {
  human_to_divine: [
    // Second person addressing pattern
    /\b(?:you|thou)\s+\w+/i,  // "you [verb]"
    /\b(?:you|thou)\s+(?:are|have been|were)\s+(?:my|our)\s+\w+/i,  // "you are my [X]"
    /\bO\s+\w+/i,  // Vocative address "O [name]"
    /\bpraise\s+(?:you|the\s+\w+)/i,  // Generic praise structure
    /\bthank\s+(?:you|the\s+\w+)/i,  // Generic thanks structure
    /\bI\s+(?:call|cry|pray|lift)\s+(?:to|unto)\s+(?:you|the\s+\w+)/i,  // Prayer verbs

    // Spanish equivalents
    /\btú\s+\w+/i,  // "tú [verbo]"
    /\boh\s+\w+/i,  // "oh [nombre]"
  ],

  primary_narration: [
    // Sequential narrative markers (domain-agnostic)
    /\bthen\s+\w+\s+\w+/i,  // "then [agent] [verb]"
    /\band\s+\w+\s+\w+/i,  // "and [agent] [verb]"
    /\bso\s+\w+\s+\w+/i,  // "so [agent] [verb]"
    /\bafter\s+(?:this|that)\s+\w+\s+\w+/i,  // "after this [agent] [verb]"
    /\band\s+(?:it|there)\s+was\b/i,  // "and it was"

    // Spanish equivalents
    /\bentonces\s+\w+\s+\w+/i,  // "entonces [agente] [verbo]"
    /\by\s+\w+\s+\w+/i,  // "y [agente] [verbo]"
  ],

  divine_direct_speech: [
    // First-person declarations (structure only)
    /\bI\s+am\s+(?:the\s+)?\w+/i,  // "I am [the] [X]"
    /\bI\s+(?:will|shall)\s+\w+/i,  // "I will [verb]"
    /\blet\s+there\s+be\b/i,  // Performative creation
    /\bI\s+have\s+\w+/i,  // "I have [verb]"

    // Spanish equivalents
    /\byo\s+soy\s+(?:el\s+)?\w+/i,  // "yo soy [el] [X]"
    /\byo\s+(?:haré|crearé)\b/i,  // Future tense markers
  ],

  human_about_divine: [
    // Third-person descriptive (structure only)
    /\b(?:he|she|it|the\s+\w+)\s+(?:is|was|has been)\s+\w+/i,  // "[subject] is [attribute]"
    /\bblessed\s+(?:be|is)\s+(?:the\s+)?\w+/i,  // "blessed be [X]"
    /\bgreat\s+is\s+(?:the\s+)?\w+/i,  // "great is [X]"

    // Spanish equivalents
    /\bél\s+es\s+\w+/i,  // "él es [atributo]"
    /\bbendito\s+(?:sea|es)\s+(?:el\s+)?\w+/i,  // "bendito sea [X]"
  ],
};

/**
 * Generates domain-specific narrative voice patterns by combining structural patterns with vocabulary.
 * @internal
 */
function generateNarrativeVoicePatterns(
  vocabulary?: DomainVocabulary
): Record<string, RegExp[]> {
  const patterns: Record<string, RegExp[]> = {
    human_to_divine: [...STRUCTURAL_NARRATIVE_VOICE_PATTERNS.human_to_divine],
    primary_narration: [...STRUCTURAL_NARRATIVE_VOICE_PATTERNS.primary_narration],
    divine_direct_speech: [...STRUCTURAL_NARRATIVE_VOICE_PATTERNS.divine_direct_speech],
    human_about_divine: [...STRUCTURAL_NARRATIVE_VOICE_PATTERNS.human_about_divine],
  };

  if (!vocabulary) {
    return patterns;
  }

  // Helper function to escape regex special characters
  const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

  // Generate agent-based patterns if agents provided
  if (vocabulary.agents && vocabulary.agents.length > 0) {
    const agentGroup = vocabulary.agents.map(escape).join('|');

    // Primary narration with specific agents + narration verbs
    if (vocabulary.narrationVerbs && vocabulary.narrationVerbs.length > 0) {
      const verbGroup = vocabulary.narrationVerbs.map(escape).join('|');
      patterns.primary_narration.push(
        new RegExp(`\\b(?:the\\s+)?(?:${agentGroup})\\s+(?:${verbGroup})\\b`, 'i'),
        new RegExp(`\\band\\s+(?:the\\s+)?(?:${agentGroup})\\s+(?:${verbGroup})\\b`, 'i'),
        new RegExp(`\\bthen\\s+(?:the\\s+)?(?:${agentGroup})\\s+(?:${verbGroup})\\b`, 'i'),
        new RegExp(`\\bso\\s+(?:the\\s+)?(?:${agentGroup})\\s+(?:${verbGroup})\\b`, 'i')
      );
    }

    // Divine direct speech with identity claims
    patterns.divine_direct_speech.push(
      new RegExp(`\\bI\\s+am\\s+(?:the\\s+)?(?:${agentGroup})\\b`, 'i')
    );

    // Human about divine with state verbs
    if (vocabulary.stateVerbs && vocabulary.stateVerbs.length > 0) {
      const stateGroup = vocabulary.stateVerbs.map(escape).join('|');
      patterns.human_about_divine.push(
        new RegExp(`\\b(?:the\\s+)?(?:${agentGroup})\\s+(?:${stateGroup})\\s+(?:my|our|a|the)\\s+\\w+`, 'i'),
        new RegExp(`\\b(?:our|my)\\s+(?:${agentGroup})\\s+(?:${stateGroup})\\b`, 'i')
      );
    }
  }

  // Generate addressee-based patterns with action verbs
  if (vocabulary.addressees && vocabulary.addressees.length > 0) {
    const addresseeGroup = vocabulary.addressees.map(escape).join('|');

    patterns.human_to_divine.push(
      new RegExp(`\\bO\\s+(?:${addresseeGroup})\\b`, 'i'),
      new RegExp(`\\b(?:${addresseeGroup}),\\s+you\\b`, 'i'),
      new RegExp(`\\bto\\s+you,?\\s+(?:O\\s+)?(?:${addresseeGroup})\\b`, 'i'),
      new RegExp(`\\bpraise\\s+(?:you|the\\s+)?(?:${addresseeGroup})`, 'i'),
      new RegExp(`\\bthank\\s+(?:you|the\\s+)?(?:${addresseeGroup})`, 'i')
    );

    // Combine addressees with action verbs for "you [verb]" pattern
    if (vocabulary.actionVerbs && vocabulary.actionVerbs.length > 0) {
      const actionGroup = vocabulary.actionVerbs.map(escape).join('|');
      patterns.human_to_divine.push(
        new RegExp(`\\b(?:you|thou)\\s+(?:${actionGroup})\\b`, 'i')
      );
    }
  }

  // Generate oracle formulas for divine direct speech
  if (vocabulary.oracleFormulas && vocabulary.oracleFormulas.length > 0) {
    for (const formula of vocabulary.oracleFormulas) {
      patterns.divine_direct_speech.push(new RegExp(`\\b${escape(formula)}\\b`, 'i'));
    }
  }

  // Generate praise formulas for human about divine
  if (vocabulary.praiseFormulas && vocabulary.praiseFormulas.length > 0) {
    for (const formula of vocabulary.praiseFormulas) {
      patterns.human_about_divine.push(new RegExp(`\\b${escape(formula)}\\b`, 'i'));
    }
  }

  return patterns;
}

/**
 * Detect the narrative voice type of a text segment.
 *
 * DOMAIN-AGNOSTIC: Accepts optional DomainVocabulary to enhance detection with domain-specific terms.
 * Works with structural patterns alone if no vocabulary provided.
 *
 * CRITICAL: This distinguishes between:
 * - Primary narration ("The agent did X") = action executed in scene
 * - Human retrospective ("You led them") = action referenced, not executed
 *
 * Use this BEFORE extracting "divine actions" to avoid confusing
 * retrospective human prayer with primary divine agency.
 *
 * @param content Text content to analyze
 * @param vocabulary Optional domain vocabulary (agents, verbs, formulas)
 * @param logger Optional logger
 */
export function detectNarrativeVoice(
  content: string,
  vocabulary?: DomainVocabulary,
  logger?: Logger
): NarrativeVoiceAnalysis {
  const indicators: string[] = [];
  let voiceType: NarrativeVoiceType = 'unknown';
  let confidence: 'high' | 'medium' | 'low' = 'low';
  let discursiveAgent: string | null = null;
  let addressee: string | null = null;
  let actionExecutionMode: NarrativeVoiceAnalysis['actionExecutionMode'] = 'none';
  let warning: string | undefined;

  // Generate patterns (structural + domain vocabulary if provided)
  const patterns = generateNarrativeVoicePatterns(vocabulary);

  // Check for HUMAN_TO_DIVINE patterns (prayer, praise) - HIGHEST PRIORITY
  for (const pattern of patterns.human_to_divine) {
    const match = content.match(pattern);
    if (match) {
      indicators.push(match[0]);
      voiceType = 'human_to_divine';
      confidence = indicators.length >= 2 ? 'high' : 'medium';
      discursiveAgent = 'human speaker';
      addressee = vocabulary?.addressees?.[0] || 'higher power';
      actionExecutionMode = 'retrospective';
      warning = 'CAUTION: This is human speech TO higher power (prayer/praise), not primary narration. Actions described are RETROSPECTIVE, not executed in-scene.';
    }
  }

  // Check for PRIMARY_NARRATION if no human-to-divine detected
  if (voiceType === 'unknown') {
    for (const pattern of patterns.primary_narration) {
      const match = content.match(pattern);
      if (match) {
        indicators.push(match[0]);
        voiceType = 'primary_narration';
        confidence = indicators.length >= 2 ? 'high' : 'medium';
        discursiveAgent = 'narrator';
        addressee = 'reader';
        actionExecutionMode = 'in_scene';
      }
    }
  }

  // Check for DIVINE_DIRECT_SPEECH
  if (voiceType === 'unknown' || voiceType === 'primary_narration') {
    for (const pattern of patterns.divine_direct_speech) {
      const match = content.match(pattern);
      if (match) {
        indicators.push(match[0]);
        if (voiceType === 'unknown') {
          voiceType = 'divine_direct_speech';
          discursiveAgent = vocabulary?.agents?.[0] || 'primary agent';
          addressee = 'audience (human/creation)';
          actionExecutionMode = 'in_scene';
        }
        confidence = indicators.length >= 2 ? 'high' : 'medium';
      }
    }
  }

  // Check for HUMAN_ABOUT_DIVINE if still unknown
  if (voiceType === 'unknown') {
    for (const pattern of patterns.human_about_divine) {
      const match = content.match(pattern);
      if (match) {
        indicators.push(match[0]);
        voiceType = 'human_about_divine';
        confidence = 'medium';
        discursiveAgent = 'human speaker';
        addressee = 'audience';
        actionExecutionMode = 'none'; // Descriptive, not action
        warning = 'This is descriptive speech about an agent, not narration of action.';
      }
    }
  }

  logger?.info('Narrative voice detected', {
    voiceType,
    confidence,
    indicators: indicators.length,
    actionExecutionMode,
    vocabularyProvided: !!vocabulary,
  });

  return {
    voiceType,
    confidence,
    indicators,
    discursiveAgent,
    addressee,
    actionExecutionMode,
    warning,
  };
}

// ============================================================================
// 8. AGENCY EXECUTION VALIDATOR
// ============================================================================

/**
 * Validates whether an action is EXECUTED in-scene vs merely REFERENCED.
 *
 * DOMAIN-AGNOSTIC: Accepts optional DomainVocabulary for enhanced detection.
 *
 * Key distinction:
 * - EXECUTED: "Fire came up from the rock and consumed the sacrifice" (primary narration)
 * - REFERENCED: "You led them with a pillar of cloud" (retrospective prayer)
 *
 * The second example describes the same action but as human retrospective memory,
 * NOT as primary narration of execution.
 *
 * @param content Text content to analyze
 * @param agentPatterns Optional agent names (e.g., ['God', 'Lord'] or ['the Court'])
 * @param vocabulary Optional domain vocabulary for comprehensive detection
 * @param logger Optional logger
 */
export function validateAgencyExecution(
  content: string,
  agentPatterns?: string[],
  vocabulary?: DomainVocabulary,
  logger?: Logger
): AgencyValidation {
  // First, detect narrative voice (pass vocabulary for enhanced detection)
  const voiceAnalysis = detectNarrativeVoice(content, vocabulary, logger);

  // Determine agency mode based on voice type
  let mode: AgencyMode = 'referenced';
  let isExecuted = false;
  let agent: string | null = null;
  let action: string | null = null;
  let verbTense: AgencyValidation['verbTense'] = 'unknown';
  const evidenceQuotes: string[] = [];
  let retrospectiveNarrator: string | undefined;
  let warning: string | undefined;

  // Helper function to escape regex special characters
  const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

  // If human-to-divine, it's automatically retrospective
  if (voiceAnalysis.voiceType === 'human_to_divine') {
    mode = 'retrospective';
    isExecuted = false;
    retrospectiveNarrator = 'human speaker (prayer/praise context)';
    warning = voiceAnalysis.warning;

    // Extract the action being referenced (use vocabulary if provided)
    if (vocabulary?.actionVerbs && vocabulary.actionVerbs.length > 0) {
      const actionGroup = vocabulary.actionVerbs.map(escape).join('|');
      const retrospectiveMatch = content.match(
        new RegExp(`\\b(?:you|thou)\\s+(${actionGroup})\\b`, 'i')
      );
      if (retrospectiveMatch) {
        action = retrospectiveMatch[1];
        evidenceQuotes.push(retrospectiveMatch[0]);
      }
    } else {
      // Fallback: generic second-person pattern
      const retrospectiveMatch = content.match(/\b(?:you|thou)\s+(\w+)/i);
      if (retrospectiveMatch) {
        action = retrospectiveMatch[1];
        evidenceQuotes.push(retrospectiveMatch[0]);
      }
    }
    verbTense = 'past'; // Retrospective is always past
  }

  // If primary narration, check for execution
  else if (voiceAnalysis.voiceType === 'primary_narration') {
    mode = 'executed';
    isExecuted = true;

    // Extract agent and action (use vocabulary/patterns if provided)
    if (agentPatterns && agentPatterns.length > 0 && vocabulary?.narrationVerbs && vocabulary.narrationVerbs.length > 0) {
      const agentGroup = agentPatterns.map(escape).join('|');
      const verbGroup = vocabulary.narrationVerbs.map(escape).join('|');
      const agentActionMatch = content.match(
        new RegExp(`\\b(?:the\\s+)?(?:${agentGroup})\\s+(${verbGroup})\\b`, 'i')
      );
      if (agentActionMatch) {
        agent = agentActionMatch[0].split(/\s+/)[0]; // Extract agent
        action = agentActionMatch[1];
        evidenceQuotes.push(agentActionMatch[0]);
      }
    } else {
      // Fallback: generic third-person pattern
      const agentActionMatch = content.match(/\b(?:the\s+)?(\w+)\s+(\w+)/i);
      if (agentActionMatch) {
        agent = agentActionMatch[1];
        action = agentActionMatch[2];
        evidenceQuotes.push(agentActionMatch[0]);
      }
    }

    // Check verb tense (use vocabulary if provided)
    if (vocabulary?.narrationVerbs && vocabulary.narrationVerbs.length > 0) {
      const pastGroup = vocabulary.narrationVerbs.map(escape).join('|');
      if (new RegExp(`\\b(${pastGroup})\\b`, 'i').test(content)) {
        verbTense = 'past';
      }
    } else {
      // Fallback: generic tense detection
      if (/\b(will|shall)\s+\w+/i.test(content)) {
        verbTense = 'future';
        mode = 'prospective';
        isExecuted = false;
      } else {
        verbTense = 'past'; // Assume past if in primary narration
      }
    }
  }

  // If divine direct speech
  else if (voiceAnalysis.voiceType === 'divine_direct_speech') {
    agent = agentPatterns?.[0] || vocabulary?.agents?.[0] || 'primary agent (speaking)';
    mode = 'executed';
    isExecuted = true;

    // Check for performative speech ("Let there be light")
    if (/\blet\s+there\s+be\b/i.test(content)) {
      action = 'performative creation';
      evidenceQuotes.push(content.match(/let\s+there\s+be\s+\w+/i)?.[0] || '');
      verbTense = 'imperative';
    }
  }

  // Check for hypothetical/conditional (use agent patterns if provided)
  if (agentPatterns && agentPatterns.length > 0) {
    const agentGroup = agentPatterns.map(escape).join('|');
    if (new RegExp(`\\bif\\s+(?:the\\s+)?(?:${agentGroup})\\b`, 'i').test(content) ||
        new RegExp(`\\bwould\\s+(?:the\\s+)?(?:${agentGroup})\\b`, 'i').test(content)) {
      mode = 'hypothetical';
      isExecuted = false;
    }
  } else {
    // Fallback: generic hypothetical pattern
    if (/\bif\s+\w+\b/i.test(content) || /\bwould\s+\w+\b/i.test(content)) {
      mode = 'hypothetical';
      isExecuted = false;
    }
  }

  // Final agent extraction if not already found
  if (!agent && agentPatterns && agentPatterns.length > 0) {
    for (const pattern of agentPatterns) {
      const regex = createPatternRegExp(pattern);
      if (regex.test(content)) {
        agent = pattern;
        break;
      }
    }
  }

  logger?.info('Agency execution validated', {
    isExecuted,
    mode,
    agent,
    action,
    verbTense,
    vocabularyProvided: !!vocabulary,
  });

  return {
    isExecuted,
    mode,
    agent,
    action,
    verbTense,
    evidenceQuotes,
    retrospectiveNarrator,
    warning,
  };
}

// ============================================================================
// 9. WEAK QUANTIFIER DETECTOR
// ============================================================================

/**
 * List of weak quantifiers that require statistical evidence.
 * Using these without evidence is a form of unsupported generalization.
 */
const WEAK_QUANTIFIERS = [
  // Frequency quantifiers
  { term: 'frequently', strength: 'strong', requiresEvidence: true },
  { term: 'often', strength: 'strong', requiresEvidence: true },
  { term: 'typically', strength: 'strong', requiresEvidence: true },
  { term: 'usually', strength: 'strong', requiresEvidence: true },
  { term: 'generally', strength: 'strong', requiresEvidence: true },
  { term: 'commonly', strength: 'strong', requiresEvidence: true },
  { term: 'rarely', strength: 'strong', requiresEvidence: true },
  { term: 'seldom', strength: 'strong', requiresEvidence: true },

  // Universal quantifiers (often unsupported)
  { term: 'always', strength: 'absolute', requiresEvidence: true },
  { term: 'never', strength: 'absolute', requiresEvidence: true },
  { term: 'every', strength: 'absolute', requiresEvidence: true },
  { term: 'all', strength: 'absolute', requiresEvidence: true },
  { term: 'none', strength: 'absolute', requiresEvidence: true },

  // Vague quantifiers
  { term: 'many', strength: 'vague', requiresEvidence: true },
  { term: 'most', strength: 'vague', requiresEvidence: true },
  { term: 'few', strength: 'vague', requiresEvidence: true },
  { term: 'some', strength: 'weak', requiresEvidence: false },
  { term: 'several', strength: 'weak', requiresEvidence: false },

  // Spanish equivalents
  { term: 'frecuentemente', strength: 'strong', requiresEvidence: true },
  { term: 'generalmente', strength: 'strong', requiresEvidence: true },
  { term: 'típicamente', strength: 'strong', requiresEvidence: true },
  { term: 'siempre', strength: 'absolute', requiresEvidence: true },
  { term: 'nunca', strength: 'absolute', requiresEvidence: true },
  { term: 'todos', strength: 'absolute', requiresEvidence: true },
  { term: 'ninguno', strength: 'absolute', requiresEvidence: true },
  { term: 'muchos', strength: 'vague', requiresEvidence: true },
  { term: 'pocos', strength: 'vague', requiresEvidence: true },
];

/**
 * Detects weak quantifiers in text that require statistical evidence.
 *
 * Quantifiers like "frequently", "typically", "generally" imply statistical
 * claims that should not be made without counting evidence.
 *
 * @param text Text to analyze (typically agent's output)
 * @param logger Optional logger
 */
export function detectWeakQuantifiers(
  text: string,
  logger?: Logger
): QuantifierValidation {
  const foundQuantifiers: WeakQuantifier[] = [];
  const lowerText = text.toLowerCase();

  for (const q of WEAK_QUANTIFIERS) {
    const regex = new RegExp(`\\b${q.term}\\b`, 'gi');
    let match;
    while ((match = regex.exec(text)) !== null) {
      // Get context (surrounding 50 chars)
      const start = Math.max(0, match.index - 25);
      const end = Math.min(text.length, match.index + q.term.length + 25);
      const context = text.slice(start, end);

      foundQuantifiers.push({
        term: q.term,
        position: match.index,
        context: `...${context}...`,
        requiresEvidence: q.requiresEvidence,
      });
    }
  }

  // Determine recommendation
  let recommendation: QuantifierValidation['recommendation'] = 'allow';
  let suggestedReplacement: string | undefined;

  const strongQuantifiers = foundQuantifiers.filter(q =>
    WEAK_QUANTIFIERS.find(wq => wq.term === q.term)?.strength === 'strong' ||
    WEAK_QUANTIFIERS.find(wq => wq.term === q.term)?.strength === 'absolute'
  );

  if (strongQuantifiers.length > 0) {
    recommendation = 'require_count';
    suggestedReplacement = 'Replace with specific counts: "in X of Y cases" or "X instances found"';

    // If absolute quantifiers without evidence, block
    const absoluteQuantifiers = foundQuantifiers.filter(q =>
      WEAK_QUANTIFIERS.find(wq => wq.term === q.term)?.strength === 'absolute'
    );
    if (absoluteQuantifiers.length > 0) {
      recommendation = 'block';
      suggestedReplacement = 'Absolute quantifiers (always/never/all/none) require complete enumeration. Use specific counts instead.';
    }
  }

  logger?.info('Weak quantifiers detected', {
    count: foundQuantifiers.length,
    requiresEvidence: strongQuantifiers.length,
    recommendation,
  });

  return {
    hasWeakQuantifiers: foundQuantifiers.length > 0,
    quantifiers: foundQuantifiers,
    recommendation,
    suggestedReplacement,
  };
}

// ============================================================================
// 10. SPEECH VS ACTION VERB CLASSIFICATION
// ============================================================================

/**
 * SPEECH_VERB_WHITELIST: Verbs that explicitly indicate speaking/communication.
 * Use this to determine if a verse contains speech.
 *
 * IMPORTANT: "command" is NOT a speech verb when used as a noun or
 * when describing divine fiat that doesn't involve literal speaking.
 */
export const SPEECH_VERB_WHITELIST = [
  // English - explicit speech acts
  'said',
  'spoke',
  'speak',
  'speaks',
  'told',
  'tell',
  'tells',
  'called',
  'call',
  'calls',
  'answered',
  'answer',
  'answers',
  'replied',
  'reply',
  'replies',
  'asked',
  'ask',
  'asks',
  'declared',
  'declare',
  'declares',
  'proclaimed',
  'proclaim',
  'proclaims',
  'cried',
  'cry',
  'cries',
  'shouted',
  'shout',
  'shouts',
  'whispered',
  'whisper',
  'whispers',
  'announced',
  'announce',
  'announces',
  'uttered',
  'utter',
  'utters',

  // Spanish equivalents
  'dijo',
  'dice',
  'habló',
  'habla',
  'llamó',
  'llama',
  'respondió',
  'responde',
  'preguntó',
  'pregunta',
  'declaró',
  'declara',
  'proclamó',
  'proclama',
  'gritó',
  'grita',
];

/**
 * CAUSAL_ACTION_VERBS: Verbs that describe action/causation WITHOUT speech.
 * Divine agency through these verbs is INDEPENDENT of speaking.
 *
 * Examples:
 * - "God caused a wind" (Genesis 8:1) - action, not speech
 * - "The Lord drove the sea back" (Exodus 14:21) - action, not speech
 * - "He rained manna" (Psalm 78:24) - action, not speech
 */
export const CAUSAL_ACTION_VERBS = [
  // English - causation/creation verbs
  'caused',
  'cause',
  'causes',
  'made',
  'make',
  'makes',
  'created',
  'create',
  'creates',
  'formed',
  'form',
  'forms',
  'sent',
  'send',
  'sends',
  'brought',
  'bring',
  'brings',
  'gave',
  'give',
  'gives',
  'placed',
  'place',
  'places',
  'set',
  'sets',
  'put',
  'puts',

  // English - physical action verbs
  'struck',
  'strike',
  'strikes',
  'drove',
  'drive',
  'drives',
  'divided',
  'divide',
  'divides',
  'split',
  'splits',
  'opened',
  'open',
  'opens',
  'closed',
  'close',
  'closes',
  'turned',
  'turn',
  'turns',
  'raised',
  'raise',
  'raises',
  'lifted',
  'lift',
  'lifts',
  'lowered',
  'lower',
  'lowers',
  'shook',
  'shake',
  'shakes',
  'moved',
  'move',
  'moves',

  // English - destruction/transformation verbs
  'destroyed',
  'destroy',
  'destroys',
  'consumed',
  'consume',
  'consumes',
  'burned',
  'burn',
  'burns',
  'drowned',
  'drown',
  'drowns',
  'scattered',
  'scatter',
  'scatters',
  'gathered',
  'gather',
  'gathers',

  // English - provision/blessing verbs
  'rained',
  'rain',
  'rains',
  'poured',
  'pour',
  'pours',
  'fed',
  'feed',
  'feeds',
  'healed',
  'heal',
  'heals',
  'blessed',
  'bless',
  'blesses',
  'saved',
  'save',
  'saves',
  'delivered',
  'deliver',
  'delivers',
  'protected',
  'protect',
  'protects',

  // English - cognitive/memory verbs (divine action without speech)
  'remembered',
  'remember',
  'remembers',
  'saw',
  'see',
  'sees',
  'heard',
  'hear',
  'hears',
  'knew',
  'know',
  'knows',
  'chose',
  'choose',
  'chooses',

  // Spanish equivalents
  'causó',
  'causa',
  'hizo',
  'hace',
  'creó',
  'crea',
  'formó',
  'forma',
  'envió',
  'envía',
  'trajo',
  'trae',
  'dio',
  'da',
  'golpeó',
  'golpea',
  'dividió',
  'divide',
  'abrió',
  'abre',
  'cerró',
  'cierra',
  'destruyó',
  'destruye',
  'sanó',
  'sana',
  'salvó',
  'salva',
  'recordó',
  'recuerda',
];

/**
 * STRUCTURAL_GENRE_PATTERNS: Domain-agnostic structural patterns for text classification.
 * These patterns identify genre based on STRUCTURE, not vocabulary.
 *
 * For domain-specific detection, the agent provides vocabularyTerms dynamically.
 */
export const STRUCTURAL_GENRE_PATTERNS = {
  /**
   * Historical narrative: Events happening in sequence (structural markers)
   * These are GENERIC patterns that work across domains.
   */
  historical_narrative: [
    /\bafter\s+(?:this|that|these\s+things)\b/i,           // Temporal sequence
    /\bin\s+(?:those|these)\s+days\b/i,                    // Historical framing
    /\bthen\s+\w+\s+(?:said|did|made|went|came)\b/i,       // Sequential action
    /\bwhen\s+\w+\s+(?:had|was|were|saw|heard)\b/i,        // Temporal clause
    /\bso\s+\w+\s+(?:did|made|went|took)\b/i,              // Consequential action
    /\band\s+it\s+(?:came\s+to\s+pass|happened)\b/i,       // Narrative formula
  ],

  /**
   * Narrative poetry: Poetic retelling with action verbs in third person
   * Generic patterns - agent provides subject terms dynamically.
   */
  narrative_poetry: [
    /\bhe\s+(?:gave|sent|made|opened|closed|struck|divided)\b/i,  // Third-person action
    /\bhe\s+(?:turned|brought|led|guided|fed|healed)\b/i,          // Third-person provision
    /\bwho\s+(?:made|created|formed|divided|struck)\b/i,           // Relative clause action
    /\bsing\s+(?:to|unto|of|about)\b/i,                            // Hymnic marker
    /\blet\s+(?:us|all|every)\b/i,                                 // Exhortation
  ],

  /**
   * Prayer/praise: Human speech addressed TO a higher power
   * Structural: second-person address + past tense verbs = retrospective
   */
  prayer_praise: [
    /\b(?:you|thou)\s+(?:led|brought|gave|made|saved|delivered|heard|answered)\b/i, // 2nd person + past
    /\bO\s+\w+\b/i,                                                 // Vocative address
    /\bwe\s+(?:praise|thank|worship|bless|glorify)\s+(?:you|thee)\b/i,  // Collective praise
    /\bhear\s+(?:our|my)\s+(?:prayer|cry|plea|voice)\b/i,          // Petition formula
    /\bto\s+(?:you|thee)\s+(?:we|I)\s+(?:cry|call|lift)\b/i,       // Address formula
  ],

  /**
   * Recapitulation: Summary of past events (memory/citation formulas)
   */
  recapitulation: [
    /\bby\s+faith\s+\w+\b/i,                                       // Faith formula
    /\bremember\s+(?:how|when|that|what)\b/i,                      // Memory invocation
    /\b(?:our|your|their)\s+(?:ancestors|fathers|forefathers)\b/i, // Generational reference
    /\bas\s+(?:it\s+is\s+written|the\s+(?:scripture|text)\s+says)\b/i, // Citation formula
    /\bin\s+(?:ancient|former|earlier)\s+(?:times|days)\b/i,       // Temporal distance
  ],

  /**
   * Prophetic: Future declarations (first-person + future tense)
   */
  prophetic: [
    /\bI\s+will\s+(?:make|bring|send|give|destroy|heal|restore)\b/i,  // First-person future
    /\bthe\s+day\s+(?:is\s+coming|will\s+come|approaches)\b/i,        // Eschatological marker
    /\bin\s+(?:that|the\s+last|those)\s+day[s]?\b/i,                  // Future time reference
    /\bbehold,?\s+I\s+(?:am|will|shall)\b/i,                          // Proclamation formula
    /\bthus\s+(?:says|declares|speaks)\b/i,                           // Oracle formula (generic)
  ],
};

/**
 * Interface for domain-specific vocabulary that the agent provides dynamically.
 * This allows ALL tools to work with ANY domain without hardcoded terms.
 *
 * Examples:
 * - Biblical: {
 *     agents: ['God', 'Lord', 'Moses'],
 *     addressees: ['Lord', 'God'],
 *     actionVerbs: ['led', 'brought', 'gave', 'made', 'created', 'saved', 'delivered'],
 *     narrationVerbs: ['said', 'spoke', 'did', 'made', 'saw', 'blessed']
 *   }
 * - Quranic: {
 *     agents: ['Allah', 'the Prophet'],
 *     addressees: ['Allah'],
 *     actionVerbs: ['guided', 'sent', 'revealed', 'blessed'],
 *     narrationVerbs: ['said', 'commanded', 'decreed']
 *   }
 * - Legal: {
 *     agents: ['the Court', 'Plaintiff', 'Defendant'],
 *     addressees: ['Your Honor'],
 *     actionVerbs: ['ruled', 'ordered', 'granted', 'denied'],
 *     narrationVerbs: ['stated', 'found', 'held', 'declared']
 *   }
 */
export interface DomainVocabulary {
  /**
   * Primary agents/actors in the text (e.g., ['God', 'Lord'] or ['Allah'] or ['the Court'])
   */
  agents?: string[];

  /**
   * Terms used when addressing a higher power/authority (e.g., ['Lord', 'God'] or ['Your Honor'])
   */
  addressees?: string[];

  /**
   * Oracle/proclamation formulas specific to the domain
   * (e.g., ['thus says the Lord'] or ['the Court finds'])
   */
  oracleFormulas?: string[];

  /**
   * Praise/worship terms specific to the domain
   * (e.g., ['praise the Lord'] or ['glory to Allah'])
   */
  praiseFormulas?: string[];

  /**
   * Action verbs used in retrospective/prayer contexts (second person)
   * (e.g., ['led', 'brought', 'gave', 'made', 'created', 'saved', 'delivered', 'healed'])
   */
  actionVerbs?: string[];

  /**
   * Narration verbs used in primary narration (third person past tense)
   * (e.g., ['said', 'spoke', 'did', 'made', 'saw', 'blessed', 'divided', 'sent'])
   */
  narrationVerbs?: string[];

  /**
   * State/identity verbs used in descriptive contexts
   * (e.g., ['is', 'was', 'has been', 'will be'])
   */
  stateVerbs?: string[];
}

/**
 * Generates domain-specific patterns by combining structural patterns with vocabulary.
 * @internal
 */
function generateDomainPatterns(
  vocabulary: DomainVocabulary
): Record<string, RegExp[]> {
  const patterns: Record<string, RegExp[]> = {
    historical_narrative: [],
    narrative_poetry: [],
    prayer_praise: [],
    prophetic: [],
  };

  // Generate agent-based patterns for historical narrative
  if (vocabulary.agents && vocabulary.agents.length > 0) {
    const agentGroup = vocabulary.agents.map(a => a.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');

    patterns.historical_narrative.push(
      new RegExp(`\\bthen\\s+(?:the\\s+)?(?:${agentGroup})\\s+(?:said|did|made)\\b`, 'i'),
      new RegExp(`\\band\\s+(?:the\\s+)?(?:${agentGroup})\\s+(?:said|did|made|saw)\\b`, 'i'),
      new RegExp(`\\bso\\s+(?:the\\s+)?(?:${agentGroup})\\s+(?:did|made)\\b`, 'i')
    );

    patterns.narrative_poetry.push(
      new RegExp(`\\b(?:our|the)\\s+(?:${agentGroup})\\s+(?:is|has|will)\\b`, 'i')
    );
  }

  // Generate addressee-based patterns for prayer/praise
  if (vocabulary.addressees && vocabulary.addressees.length > 0) {
    const addresseeGroup = vocabulary.addressees.map(a => a.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');

    patterns.prayer_praise.push(
      new RegExp(`\\bO\\s+(?:${addresseeGroup})\\b`, 'i'),
      new RegExp(`\\bto\\s+(?:you|thee),?\\s+(?:O\\s+)?(?:${addresseeGroup})\\b`, 'i')
    );
  }

  // Generate oracle formulas for prophetic
  if (vocabulary.oracleFormulas && vocabulary.oracleFormulas.length > 0) {
    for (const formula of vocabulary.oracleFormulas) {
      const escaped = formula.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      patterns.prophetic.push(new RegExp(`\\b${escaped}\\b`, 'i'));
    }
  }

  // Generate praise formulas
  if (vocabulary.praiseFormulas && vocabulary.praiseFormulas.length > 0) {
    for (const formula of vocabulary.praiseFormulas) {
      const escaped = formula.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      patterns.narrative_poetry.push(new RegExp(`\\b${escaped}\\b`, 'i'));
    }
  }

  return patterns;
}

// Keep legacy export name for backward compatibility, but mark as deprecated
/** @deprecated Use STRUCTURAL_GENRE_PATTERNS instead */
export const TEXT_GENRE_INDICATORS = STRUCTURAL_GENRE_PATTERNS;

export type TextGenre =
  | 'historical_narrative'
  | 'narrative_poetry'
  | 'prayer_praise'
  | 'recapitulation'
  | 'prophetic'
  | 'unknown';

export interface TextGenreAnalysis {
  genre: TextGenre;
  confidence: 'high' | 'medium' | 'low';
  indicators: string[];
  extractionRules: {
    actionsAreExecuted: boolean;
    allowRetrospective: boolean;
    requireSpeechForAction: boolean;
  };
  warning?: string;
}

/**
 * Result of agency-without-speech detection.
 * Renamed from DivineAgencyWithoutSpeechResult to be domain-agnostic.
 */
export interface AgencyWithoutSpeechResult {
  /** Whether agency without speech was found */
  found: boolean;
  /** The agent performing the action (null if no agent patterns provided or not found) */
  agent: string | null;
  /** The action verb found */
  actionVerb: string | null;
  /** Whether any speech verbs were found in the text */
  hasSpeechVerb: boolean;
  /** List of speech verbs found */
  speechVerbsFound: string[];
  /** List of action verbs found */
  actionVerbsFound: string[];
  /** Detected verb tense */
  verbTense: 'past' | 'present' | 'future' | 'imperative' | 'unknown';
  /** Whether we have complete text unit (verse) */
  isComplete: boolean;
  /** Detected text genre */
  genre: TextGenre;
  /** Confidence level */
  confidence: 'high' | 'medium' | 'low';
  /** Warning message if any */
  warning?: string;
  /** Whether agent patterns were provided */
  agentPatternsProvided: boolean;
}

/** @deprecated Use AgencyWithoutSpeechResult instead */
export type DivineAgencyWithoutSpeechResult = AgencyWithoutSpeechResult;

/**
 * Detects the text genre to apply appropriate extraction rules.
 *
 * DOMAIN-AGNOSTIC: Uses structural patterns by default.
 * For domain-specific detection, provide domainVocabulary.
 *
 * @param content Text content to analyze
 * @param domainVocabulary Optional domain-specific vocabulary for enhanced detection
 * @param logger Optional logger
 *
 * @example
 * // Generic detection (structural patterns only)
 * detectTextGenre(content);
 *
 * @example
 * // Biblical context
 * detectTextGenre(content, {
 *   agents: ['God', 'Lord', 'Moses'],
 *   addressees: ['Lord', 'God'],
 *   oracleFormulas: ['thus says the Lord'],
 *   praiseFormulas: ['praise the Lord']
 * });
 *
 * @example
 * // Legal context
 * detectTextGenre(content, {
 *   agents: ['the Court', 'Plaintiff', 'Defendant'],
 *   addressees: ['Your Honor'],
 *   oracleFormulas: ['the Court finds', 'it is hereby ordered']
 * });
 */
export function detectTextGenre(
  content: string,
  domainVocabulary?: DomainVocabulary,
  logger?: Logger
): TextGenreAnalysis {
  const genreScores: Record<TextGenre, { score: number; indicators: string[] }> = {
    historical_narrative: { score: 0, indicators: [] },
    narrative_poetry: { score: 0, indicators: [] },
    prayer_praise: { score: 0, indicators: [] },
    recapitulation: { score: 0, indicators: [] },
    prophetic: { score: 0, indicators: [] },
    unknown: { score: 0, indicators: [] },
  };

  // Step 1: Apply structural (domain-agnostic) patterns
  for (const [genre, patterns] of Object.entries(STRUCTURAL_GENRE_PATTERNS)) {
    for (const pattern of patterns) {
      const match = content.match(pattern);
      if (match) {
        genreScores[genre as TextGenre].score++;
        genreScores[genre as TextGenre].indicators.push(match[0]);
      }
    }
  }

  // Step 2: Apply domain-specific patterns if vocabulary provided
  if (domainVocabulary) {
    const domainPatterns = generateDomainPatterns(domainVocabulary);

    for (const [genre, patterns] of Object.entries(domainPatterns)) {
      for (const pattern of patterns) {
        const match = content.match(pattern);
        if (match) {
          // Domain-specific matches get extra weight
          genreScores[genre as TextGenre].score += 1.5;
          genreScores[genre as TextGenre].indicators.push(`[domain] ${match[0]}`);
        }
      }
    }
  }

  // Find highest scoring genre
  let bestGenre: TextGenre = 'unknown';
  let bestScore = 0;
  for (const [genre, data] of Object.entries(genreScores)) {
    if (data.score > bestScore) {
      bestScore = data.score;
      bestGenre = genre as TextGenre;
    }
  }

  // Determine confidence
  let confidence: 'high' | 'medium' | 'low' = 'low';
  if (bestScore >= 3) confidence = 'high';
  else if (bestScore >= 2) confidence = 'medium';

  // Set extraction rules based on genre
  const extractionRules = {
    actionsAreExecuted: bestGenre === 'historical_narrative',
    allowRetrospective: bestGenre === 'prayer_praise' || bestGenre === 'recapitulation',
    requireSpeechForAction: false, // This was the key error - should be FALSE
  };

  let warning: string | undefined;
  if (bestGenre === 'prayer_praise') {
    warning = 'CAUTION: Prayer/praise genre - actions described are RETROSPECTIVE, not executed in-scene.';
  } else if (bestGenre === 'narrative_poetry') {
    warning = 'NOTE: Narrative poetry may describe action without explicit speech context.';
  }

  logger?.info('Text genre detected', {
    genre: bestGenre,
    confidence,
    score: bestScore,
    hasDomainVocabulary: !!domainVocabulary,
  });

  return {
    genre: bestGenre,
    confidence,
    indicators: genreScores[bestGenre].indicators,
    extractionRules,
    warning,
  };
}

/**
 * Detects agency WITHOUT speech in a text segment.
 *
 * DOMAIN-AGNOSTIC: Works with any document type.
 * Agent provides agentPatterns dynamically based on document context.
 *
 * Examples:
 * - Biblical: agentPatterns = ['God', 'Lord', 'the Lord']
 *   Finds: "God remembered Noah", "The Lord drove the sea back"
 *
 * - Quranic: agentPatterns = ['Allah', 'the Prophet']
 *   Finds: "Allah guided them", "the Prophet led them"
 *
 * - Legal: agentPatterns = ['the Court', 'the Judge']
 *   Finds: "the Court ruled", "the Judge dismissed"
 *
 * - Literary: agentPatterns = ['the King', 'the Hero']
 *   Finds: "the King decreed", "the Hero saved"
 *
 * The function:
 * 1. Checks if any SPEECH verbs are present
 * 2. If agentPatterns provided, checks if any action verbs have that agent as subject
 * 3. Returns whether agency exists WITHOUT speech
 *
 * @param content Text content to analyze
 * @param agentPatterns Agent names to search for (e.g., ['God', 'Lord'] or ['the Court'])
 * @param domainVocabulary Optional domain vocabulary for genre detection
 * @param logger Optional logger
 */
export function detectDivineAgencyWithoutSpeech(
  content: string,
  agentPatterns?: string[],
  domainVocabulary?: DomainVocabulary,
  logger?: Logger
): AgencyWithoutSpeechResult {
  const speechVerbsFound: string[] = [];
  const actionVerbsFound: string[] = [];
  let agent: string | null = null;
  let actionVerb: string | null = null;
  let verbTense: AgencyWithoutSpeechResult['verbTense'] = 'unknown';

  const agentPatternsProvided = agentPatterns !== undefined && agentPatterns.length > 0;

  // Step 1: Check for speech verbs
  for (const verb of SPEECH_VERB_WHITELIST) {
    const regex = new RegExp(`\\b${verb}\\b`, 'i');
    if (regex.test(content)) {
      speechVerbsFound.push(verb);
    }
  }

  // Step 2: Check for causal/action verbs
  for (const verb of CAUSAL_ACTION_VERBS) {
    const regex = new RegExp(`\\b${verb}\\b`, 'i');
    if (regex.test(content)) {
      actionVerbsFound.push(verb);

      // Only check for specific agent if patterns provided
      if (agentPatternsProvided) {
        for (const agentPattern of agentPatterns!) {
          // Escape special regex characters in agent pattern
          const escapedAgent = agentPattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

          // Pattern: "Agent + verb" or "the Agent + verb"
          const subjectVerbRegex = new RegExp(
            `\\b(?:the\\s+)?${escapedAgent}\\s+(?:\\w+\\s+)?${verb}\\b`,
            'i'
          );
          if (subjectVerbRegex.test(content)) {
            agent = agentPattern;
            actionVerb = verb;
          }

          // Also check for "he/she/it" when agent mentioned earlier
          if (!agent && /\b(?:he|she|it)\s+/i.test(content)) {
            const agentMentionedFirst = new RegExp(
              `\\b(?:the\\s+)?(?:${agentPatterns!.map(a => a.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})\\b.*\\b(?:he|she|it)\\s+${verb}\\b`,
              'i'
            );
            if (agentMentionedFirst.test(content)) {
              agent = `pronoun (referring to ${agentPattern})`;
              actionVerb = verb;
            }
          }
        }
      }
    }
  }

  // Step 3: Determine verb tense
  const pastTenseIndicators = /\b(was|were|had|did|made|gave|sent|caused|drove|opened|closed|struck|created|formed|rained|remembered|saw|brought|led|divided|destroyed|healed|saved|delivered)\b/i;
  const presentTenseIndicators = /\b(is|are|has|does|makes|gives|sends|causes|drives|opens|closes|strikes|creates|forms|rains|remembers|sees|brings|leads|divides|destroys|heals|saves|delivers)\b/i;
  const futureTenseIndicators = /\b(will|shall)\s+\w+/i;

  if (pastTenseIndicators.test(content)) verbTense = 'past';
  else if (presentTenseIndicators.test(content)) verbTense = 'present';
  else if (futureTenseIndicators.test(content)) verbTense = 'future';

  // Step 4: Detect genre (pass domain vocabulary if provided)
  const genreAnalysis = detectTextGenre(content, domainVocabulary, logger);

  // Step 5: Determine if agency without speech is found
  const hasSpeechVerb = speechVerbsFound.length > 0;

  // If agent patterns provided, require agent match
  // If not provided, just check for action verbs without speech
  const hasActionVerb = agentPatternsProvided
    ? (actionVerbsFound.length > 0 && agent !== null)
    : (actionVerbsFound.length > 0);

  const found = hasActionVerb && !hasSpeechVerb;

  // Determine confidence
  let confidence: 'high' | 'medium' | 'low' = 'low';
  if (found && actionVerbsFound.length > 0) {
    if (agentPatternsProvided && agent && actionVerb) {
      confidence = verbTense === 'past' ? 'high' : 'medium';
    } else if (!agentPatternsProvided) {
      // Without agent patterns, confidence is based on action verbs only
      confidence = verbTense === 'past' ? 'medium' : 'low';
    }
  }

  let warning: string | undefined;
  if (!agentPatternsProvided) {
    warning = 'NOTE: No agent patterns provided. Detection is based on action verbs only, without agent attribution.';
  } else if (found && genreAnalysis.genre === 'prayer_praise') {
    warning = 'CAUTION: Found in prayer/praise context - action may be RETROSPECTIVE, not executed in-scene.';
  } else if (found && genreAnalysis.genre === 'narrative_poetry') {
    warning = 'NOTE: Found in narrative poetry - verify this is primary narration, not retrospective.';
  }

  logger?.info('Agency without speech detection', {
    found,
    agent,
    actionVerb,
    hasSpeechVerb,
    speechVerbsFound: speechVerbsFound.length,
    actionVerbsFound: actionVerbsFound.length,
    verbTense,
    genre: genreAnalysis.genre,
    agentPatternsProvided,
  });

  return {
    found,
    agent,
    actionVerb,
    hasSpeechVerb,
    speechVerbsFound,
    actionVerbsFound,
    verbTense,
    isComplete: true, // Assume complete unless chunked
    genre: genreAnalysis.genre,
    confidence,
    warning,
    agentPatternsProvided,
  };
}

// ============================================================================
// 11. EVASION PATTERN DETECTOR
// ============================================================================

/**
 * Patterns that indicate the agent is evading instead of answering.
 * These are HARD VIOLATIONS in existential questions.
 */
const EVASION_PATTERNS = {
  // Agent blames tool/system limitations
  limitation_excuse: [
    /\bno puedo\s+(?:enumerar|listar|confirmar|verificar|demostrar)\b/i,
    /\bcannot\s+(?:enumerate|list|confirm|verify|demonstrate)\b/i,
    /\blimitaciones?\s+(?:de|del)\s+(?:la\s+)?(?:tool|herramienta|sistema|indexaci[oó]n)/i,
    /\blimitation[s]?\s+(?:of|in)\s+(?:the\s+)?(?:tool|system|indexing)/i,
    /\bdue to\s+(?:the\s+)?(?:chunking|segmentation|indexing)\b/i,
    /\bdebido a\s+(?:la\s+)?(?:fragmentaci[oó]n|segmentaci[oó]n)\b/i,
    /\bthe\s+(?:tool|system)\s+(?:cannot|doesn't|does not)\b/i,
    /\bla\s+(?:herramienta|tool)\s+no\s+(?:puede|permite)\b/i,
  ],

  // Meta-discourse instead of answering
  meta_discourse: [
    /\bpara\s+responder\s+(?:esta|tu|la)\s+pregunta\b/i,
    /\bto\s+answer\s+(?:this|your|the)\s+question\b/i,
    /\bel\s+problema\s+t[eé]cnico\b/i,
    /\bthe\s+technical\s+problem\b/i,
    /\bhallazgo[s]?\s*:/i,
    /\bfinding[s]?\s*:/i,
    /\bdiagn[oó]stico\b/i,
    /\bdiagnosis\b/i,
    /\banálisis\s+previo\b/i,
    /\bprior\s+analysis\b/i,
  ],

  // Asking for permission instead of answering
  unnecessary_question: [
    /\b¿(?:quieres|deseas|prefieres)\s+que\b/i,
    /\bwould\s+you\s+(?:like|prefer|want)\s+(?:me\s+to|that\s+I)\b/i,
    /\b¿te\s+(?:gustar[ií]a|parece)\b/i,
    /\bshould\s+I\s+(?:try|attempt)\b/i,
    /\b¿(?:debo|debería)\s+intentar\b/i,
  ],

  // Introducing categories not asked for
  category_introduction: [
    /\bTIPO\s+[A-Z]\s*(?:\(|:)/i,
    /\bTYPE\s+[A-Z]\s*(?:\(|:)/i,
    /\bcategor[ií]a[s]?\s*(?:\d|[A-Z])\b/i,
    /\bcategory\s+(?:\d|[A-Z])\b/i,
    /\bpatr[oó]n\s+estructural\b/i,
    /\bstructural\s+pattern\b/i,
    /\btipolog[ií]a[s]?\b/i,
    /\btypolog(?:y|ies)\b/i,
  ],

  // Hedging without evidence
  hedging: [
    /\bprobablemente\s+(?:existen?|hay)\b/i,
    /\bprobably\s+(?:exist[s]?|there\s+(?:are|is))\b/i,
    /\bparece\s+(?:que|ser)\b/i,
    /\bit\s+(?:seems|appears)\s+(?:that|to\s+be)\b/i,
    /\bpodr[ií]an?\s+existir\b/i,
    /\b(?:could|might|may)\s+exist\b/i,
    /\bes\s+posible\s+que\b/i,
    /\bit(?:'s|\s+is)\s+possible\s+that\b/i,
  ],

  // Probability claims without statistical evidence
  probability_without_evidence: [
    /\b(?:mayoritariamente|principalmente|frecuentemente)\b/i,
    /\b(?:mostly|mainly|frequently)\b/i,
    /\bla\s+mayor[ií]a\s+de\b/i,
    /\bmost\s+of\s+(?:the|these)\b/i,
    /\bson\s+(?:raros?|excepcionales?|minoritarios?)\b/i,
    /\bare\s+(?:rare|exceptional|minority)\b/i,
    /\b(?:muy\s+)?(?:poco|rara)\s+(?:común|frecuente)\b/i,
    /\b(?:very\s+)?(?:un)?common\b/i,
  ],
};

/**
 * Detects evasion patterns in agent output.
 *
 * Use this to validate responses to existential questions.
 * Any detected pattern is a VIOLATION that invalidates the response.
 *
 * @param text Agent's response text
 * @param logger Optional logger
 */
export function detectEvasionPatterns(
  text: string,
  logger?: Logger
): EvasionPattern[] {
  const patterns: EvasionPattern[] = [];

  for (const [type, regexList] of Object.entries(EVASION_PATTERNS)) {
    for (const regex of regexList) {
      const match = text.match(regex);
      if (match) {
        patterns.push({
          type: type as EvasionPattern['type'],
          matchedText: match[0],
          severity: type === 'hedging' ? 'warning' : 'violation',
        });
      }
    }
  }

  logger?.info('Evasion patterns detected', {
    count: patterns.length,
    violations: patterns.filter(p => p.severity === 'violation').length,
  });

  return patterns;
}

// ============================================================================
// 11. EXISTENTIAL RESPONSE VALIDATOR
// ============================================================================

/**
 * Patterns indicating affirmative response with evidence
 */
const AFFIRMATIVE_PATTERNS = [
  /\bSÍ\b/i,
  /\bYES\b/i,
  /\bexiste[n]?\b/i,
  /\bexist[s]?\b/i,
  /\bhay\b/i,
  /\bthere\s+(?:is|are)\b/i,
  /\bencontr[eéó]\b/i,
  /\bfound\b/i,
];

/**
 * Patterns indicating explicit denial
 */
const DENIAL_PATTERNS = [
  /\bNO\b(?!\s+(?:puedo|puede|hay|existe|encontr))/,
  /\bno\s+(?:existe[n]?|hay|encontr[eéó])\b/i,
  /\bdoes\s+not\s+exist\b/i,
  /\bdo\s+not\s+exist\b/i,
  /\bthere\s+(?:is|are)\s+no\b/i,
  /\bnot\s+found\b/i,
  /\bno\s+(?:verse[s]?|text|evidence)\b/i,
  /\bningún\s+(?:verso?|texto|evidencia)\b/i,
];

/**
 * Validates that a response to an existential question meets the contract:
 *
 * VALID responses:
 * - "YES" + at least one concrete textual quote/reference
 * - "NO" + explicit statement that X does not exist in the corpus
 *
 * INVALID responses:
 * - Meta-discourse about limitations
 * - Hedging ("probably", "might exist")
 * - Category introductions not asked for
 * - Asking follow-up questions instead of answering
 * - Claiming existence without evidence
 *
 * @param response Agent's response text
 * @param logger Optional logger
 */
export function validateExistentialResponse(
  response: string,
  logger?: Logger
): ExistentialResponseValidation {
  const violations: string[] = [];
  const evidence: ExistentialEvidence[] = [];

  // Step 1: Detect evasion patterns
  const evasionPatterns = detectEvasionPatterns(response, logger);

  // Any violation-level evasion = automatic failure
  const hardViolations = evasionPatterns.filter(p => p.severity === 'violation');
  if (hardViolations.length > 0) {
    for (const v of hardViolations) {
      violations.push(`EVASION [${v.type}]: "${v.matchedText}"`);
    }
  }

  // Step 2: Check for affirmative response with evidence
  const hasAffirmative = AFFIRMATIVE_PATTERNS.some(p => p.test(response));

  // Step 3: Check for explicit denial
  const hasDenial = DENIAL_PATTERNS.some(p => p.test(response));

  // Step 4: Extract potential evidence (quoted text)
  const quoteMatches = response.matchAll(/["«"]([^"»"]{10,})["»"]/g);
  for (const match of quoteMatches) {
    evidence.push({
      quote: match[1],
      verified: false, // Would need to verify against source
    });
  }

  // Also check for verse references like "Genesis 1:3" or "Exodus 33:20"
  const verseRefs = response.matchAll(/\b([1-3]?\s*[A-Z][a-z]+)\s+(\d+):(\d+(?:-\d+)?)\b/g);
  for (const match of verseRefs) {
    evidence.push({
      quote: match[0],
      location: match[0],
      verified: false,
    });
  }

  // Step 5: Determine response type
  let responseType: ExistentialResponseType = 'malformed';
  let requiredAction: ExistentialResponseValidation['requiredAction'] = 'retry';

  if (hardViolations.length > 0) {
    responseType = 'evaded';
    requiredAction = 'remove_meta_discourse';
  } else if (hasAffirmative && evidence.length > 0) {
    responseType = 'affirmed';
    requiredAction = 'none';
  } else if (hasAffirmative && evidence.length === 0) {
    responseType = 'evaded';
    violations.push('AFFIRMED without evidence: Response says YES but provides no textual quote');
    requiredAction = 'provide_evidence';
  } else if (hasDenial) {
    responseType = 'denied';
    requiredAction = 'none';
  } else {
    responseType = 'malformed';
    violations.push('NO_CLEAR_ANSWER: Response neither affirms nor denies existence');
    requiredAction = 'retry';
  }

  const isValid = responseType === 'affirmed' || responseType === 'denied';

  logger?.info('Existential response validated', {
    isValid,
    responseType,
    evidenceCount: evidence.length,
    violationCount: violations.length,
    requiredAction,
  });

  return {
    isValid,
    responseType,
    evidence,
    evasionPatterns,
    violations,
    requiredAction,
  };
}

// ============================================================================
// 12. SAFE FALLBACK GENERATOR FOR EXISTENTIAL QUESTIONS
// ============================================================================

/**
 * Generates a compliant fallback response when the agent cannot answer
 * an existential question after genuine search.
 *
 * This forces the agent to commit to YES or NO instead of hedging.
 *
 * @param searchPerformed Whether a genuine search was performed
 * @param resultsFound Number of matching results found
 * @param documentTitle Title of the document searched
 */
export function generateExistentialFallback(
  searchPerformed: boolean,
  resultsFound: number,
  documentTitle: string
): { response: string; responseType: ExistentialResponseType } {
  if (!searchPerformed) {
    return {
      response: `NO. No search was performed on "${documentTitle}".`,
      responseType: 'denied',
    };
  }

  if (resultsFound === 0) {
    return {
      response: `NO. Searched "${documentTitle}" and found no matching text.`,
      responseType: 'denied',
    };
  }

  // If results were found but couldn't be verified, still commit
  return {
    response: `INCONCLUSIVE. Found ${resultsFound} potential matches in "${documentTitle}" but could not verify exact criteria. Requires manual review.`,
    responseType: 'malformed', // Forces retry with better search
  };
}

// ============================================================================
// EXPORTS
// ============================================================================

export {
  COMMENTARY_INDICATORS,
  SPEECH_MARKERS,
  STRUCTURAL_NARRATIVE_VOICE_PATTERNS,
  WEAK_QUANTIFIERS,
  // Note: SPEECH_VERB_WHITELIST, CAUSAL_ACTION_VERBS, STRUCTURAL_GENRE_PATTERNS are already exported at declaration
  // Note: DomainVocabulary interface is already exported at declaration
  normalizeText,
  calculateSimilarity,
};

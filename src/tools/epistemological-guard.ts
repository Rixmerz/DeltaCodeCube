import Database from 'better-sqlite3';
import { Logger } from '../utils/logger.js';
import { analyzeSourceCapabilities, type SourceCapabilities } from './source-validation.js';

/**
 * Epistemological Guard Module
 *
 * Enforces strict boundaries between document content, editorial notes,
 * and external knowledge. Prevents hallucinated grounding.
 */

// ============================================================================
// SOURCE TAGGING SYSTEM
// ============================================================================

export type SourceTag = 'DOC' | 'NOTE' | 'EXT' | 'INFERRED';

export interface TaggedClaim {
  claim: string;
  tag: SourceTag;
  confidence: 'high' | 'medium' | 'low';
  basis: string;
  indeterminacy: 'high' | 'medium' | 'low';
  textualSpan?: string;  // Exact quote from document if DOC/NOTE
  externalSource?: string;  // Citation if EXT
}

export interface TaggingRules {
  requireTextualSpan: boolean;
  allowExternalKnowledge: boolean;
  requireExternalCitation: boolean;
  maxInferenceDepth: number;
}

const STRICT_RULES: TaggingRules = {
  requireTextualSpan: true,
  allowExternalKnowledge: false,
  requireExternalCitation: true,
  maxInferenceDepth: 1,
};

const PERMISSIVE_RULES: TaggingRules = {
  requireTextualSpan: false,
  allowExternalKnowledge: true,
  requireExternalCitation: false,
  maxInferenceDepth: 3,
};

// ============================================================================
// HARD STOP RULES BY LANGUAGE
// ============================================================================

export interface LanguageHardStop {
  language: string;
  presentInDocument: boolean;
  allowedOperations: string[];
  blockedOperations: string[];
}

const LANGUAGE_OPERATIONS = {
  morphological: ['root analysis', 'stem analysis', 'conjugation', 'declension', 'parsing'],
  etymological: ['etymology', 'word origin', 'cognate analysis', 'semantic field'],
  textualCritical: ['variant analysis', 'manuscript comparison', 'critical apparatus'],
  translational: ['translation comparison', 'rendering choice', 'semantic range'],
  quotational: ['direct quotation', 'citation', 'text reference'],
};

export function getLanguageHardStops(
  capabilities: SourceCapabilities
): LanguageHardStop[] {
  const stops: LanguageHardStop[] = [];

  // Hebrew rules
  const hasHebrew = capabilities.detectedLanguages.includes('hebrew');
  stops.push({
    language: 'hebrew',
    presentInDocument: hasHebrew,
    allowedOperations: hasHebrew
      ? [...LANGUAGE_OPERATIONS.morphological, ...LANGUAGE_OPERATIONS.quotational]
      : ['transliteration reference only'],
    blockedOperations: hasHebrew
      ? []
      : [...LANGUAGE_OPERATIONS.morphological, ...LANGUAGE_OPERATIONS.etymological],
  });

  // Greek rules
  const hasGreek = capabilities.detectedLanguages.includes('greek');
  stops.push({
    language: 'greek',
    presentInDocument: hasGreek,
    allowedOperations: hasGreek
      ? [...LANGUAGE_OPERATIONS.morphological, ...LANGUAGE_OPERATIONS.quotational]
      : ['transliteration reference only'],
    blockedOperations: hasGreek
      ? []
      : [...LANGUAGE_OPERATIONS.morphological, ...LANGUAGE_OPERATIONS.etymological],
  });

  // Aramaic rules
  const hasAramaic = capabilities.detectedLanguages.includes('aramaic');
  stops.push({
    language: 'aramaic',
    presentInDocument: hasAramaic,
    allowedOperations: hasAramaic
      ? [...LANGUAGE_OPERATIONS.morphological, ...LANGUAGE_OPERATIONS.quotational]
      : ['transliteration reference only'],
    blockedOperations: hasAramaic
      ? []
      : [...LANGUAGE_OPERATIONS.morphological, ...LANGUAGE_OPERATIONS.etymological],
  });

  return stops;
}

export function checkOperationAllowed(
  operation: string,
  language: string,
  hardStops: LanguageHardStop[]
): { allowed: boolean; reason: string } {
  const stop = hardStops.find(s => s.language === language);

  if (!stop) {
    return { allowed: false, reason: `Unknown language: ${language}` };
  }

  // Check if operation is explicitly blocked
  for (const blocked of stop.blockedOperations) {
    if (operation.toLowerCase().includes(blocked.toLowerCase())) {
      return {
        allowed: false,
        reason: `HARD STOP: "${operation}" requires ${language} text which is not present in document. ` +
          `Allowed operations: ${stop.allowedOperations.join(', ')}`,
      };
    }
  }

  return { allowed: true, reason: 'Operation permitted' };
}

// ============================================================================
// TEMPLE THEOLOGY DETECTION (Critique: assumed without penalty)
// ============================================================================

/**
 * Detects when temple theology concepts are invoked without explicit textual support.
 * Temple theology = Name dwelling, shekinah, tabernacle presence, sacred space.
 * These require specific passages (Exodus 25, Deuteronomy 12, etc.) to ground.
 */
export interface TempleTheologyPenalty {
  detected: boolean;
  concepts: string[];
  hasExplicitPassage: boolean;
  penalty: number;  // 0-0.3 confidence reduction
  warning: string | null;
  requiredGrounding: string[];
}

const TEMPLE_THEOLOGY_CONCEPTS = [
  {
    pattern: /\b(dwell(?:ing|s)?|tabernacle|sanctuary|temple)\b.*\b(name|presence|glory)\b/i,
    concept: 'Name-dwelling theology',
    requiredPassages: ['Exodus 25:8', 'Exodus 29:45-46', 'Deuteronomy 12:5', '1 Kings 8:29'],
  },
  {
    pattern: /\b(shekinah|glory cloud|kavod)\b/i,
    concept: 'Shekinah presence',
    requiredPassages: ['Exodus 40:34-38', 'Ezekiel 10:4', 'Ezekiel 43:2-5'],
  },
  {
    pattern: /\bsacred space\b/i,
    concept: 'Sacred space theology',
    requiredPassages: ['Exodus 3:5', 'Exodus 19:12', 'Leviticus 16'],
  },
  {
    pattern: /\bname\b.*\b(place|house|dwell)\b/i,
    concept: 'Deuteronomic Name theology',
    requiredPassages: ['Deuteronomy 12:5', 'Deuteronomy 12:11', 'Deuteronomy 14:23'],
  },
  {
    pattern: /\b(holy of holies|most holy place|inner sanctuary)\b/i,
    concept: 'Tabernacle/Temple structure',
    requiredPassages: ['Exodus 26:33-34', 'Leviticus 16:2', '1 Kings 6:16'],
  },
];

export function detectTempleTheologyPenalty(
  content: string,
  query: string
): TempleTheologyPenalty {
  const detected: { concept: string; passages: string[] }[] = [];
  const combinedText = `${content} ${query}`.toLowerCase();

  for (const { pattern, concept, requiredPassages } of TEMPLE_THEOLOGY_CONCEPTS) {
    if (pattern.test(combinedText)) {
      detected.push({ concept, passages: requiredPassages });
    }
  }

  if (detected.length === 0) {
    return {
      detected: false,
      concepts: [],
      hasExplicitPassage: false,
      penalty: 0,
      warning: null,
      requiredGrounding: [],
    };
  }

  // Check if any required passages are explicitly mentioned
  const allRequiredPassages = detected.flatMap(d => d.passages);
  const hasExplicitPassage = allRequiredPassages.some(passage => {
    const bookChapter = passage.split(':')[0];
    return content.toLowerCase().includes(bookChapter.toLowerCase());
  });

  // Calculate penalty: higher if no explicit passage grounds the claim
  const basePenalty = 0.15;
  const penalty = hasExplicitPassage ? basePenalty * 0.3 : basePenalty;

  return {
    detected: true,
    concepts: detected.map(d => d.concept),
    hasExplicitPassage,
    penalty,
    warning: hasExplicitPassage
      ? null
      : `TEMPLE THEOLOGY WARNING: ${detected.map(d => d.concept).join(', ')} invoked without explicit passage support. ` +
        `Confidence reduced by ${(penalty * 100).toFixed(0)}%. ` +
        `Grounding requires: ${allRequiredPassages.slice(0, 3).join(', ')}...`,
    requiredGrounding: allRequiredPassages,
  };
}

// ============================================================================
// PHILOSOPHICAL INFERENCE DETECTION (Critique: mark non-explicit claims)
// ============================================================================

/**
 * Detects philosophical inferences that are NOT explicit in the text.
 * E.g., "Logos as condition of intelligibility" is a philosophical reading,
 * not a direct textual claim.
 */
export interface PhilosophicalInference {
  claim: string;
  isExplicit: boolean;
  inferenceType: 'philosophical' | 'theological' | 'historical' | 'linguistic';
  textualAnchor: string | null;
  confidenceReduction: number;
  warning: string;
}

const PHILOSOPHICAL_CLAIMS = [
  {
    pattern: /\bcondition of intelligibility\b/i,
    type: 'philosophical' as const,
    warning: 'This is a philosophical (Kantian/phenomenological) interpretation, not explicit in text.',
    reduction: 0.15,
  },
  {
    pattern: /\b(ground of being|being itself|ontological ground)\b/i,
    type: 'philosophical' as const,
    warning: 'This is Tillichian/existentialist language not found in ancient texts.',
    reduction: 0.15,
  },
  {
    pattern: /\b(cosmic reason|universal rationality|rational order)\b/i,
    type: 'philosophical' as const,
    warning: 'This is Stoic Logos doctrine, not necessarily equivalent to Johannine usage.',
    reduction: 0.12,
  },
  {
    pattern: /\b(hypostatic|hypostasis|person of the trinity)\b/i,
    type: 'theological' as const,
    warning: 'This is post-Nicene terminology (4th century CE), anachronistic to text composition.',
    reduction: 0.18,
  },
  {
    pattern: /\b(pre-existent|pre-existence|eternal generation)\b/i,
    type: 'theological' as const,
    warning: 'These are later theological categories; text may support but does not explicitly state.',
    reduction: 0.10,
  },
  {
    pattern: /\b(agent of creation|instrumental cause|mediator of creation)\b/i,
    type: 'theological' as const,
    warning: 'Causality language imports Aristotelian categories; text uses "through" without defining mechanism.',
    reduction: 0.08,
  },
];

export function detectPhilosophicalInferences(query: string): PhilosophicalInference[] {
  const inferences: PhilosophicalInference[] = [];

  for (const { pattern, type, warning, reduction } of PHILOSOPHICAL_CLAIMS) {
    const match = query.match(pattern);
    if (match) {
      inferences.push({
        claim: match[0],
        isExplicit: false,
        inferenceType: type,
        textualAnchor: null,
        confidenceReduction: reduction,
        warning: `INFERENCE DETECTED [${type.toUpperCase()}]: "${match[0]}" - ${warning}`,
      });
    }
  }

  return inferences;
}

// ============================================================================
// AUTO-CRITIQUE GENERATOR
// ============================================================================

export interface AutoCritique {
  cannotResolve: string[];
  assumptionsMade: string[];
  alternativeFramings: string[];
  confidenceGaps: string[];
  canonicalBias?: string;
}

export function generateAutoCritique(
  query: string,
  capabilities: SourceCapabilities,
  claimsAnalyzed: number
): AutoCritique {
  const critique: AutoCritique = {
    cannotResolve: [],
    assumptionsMade: [],
    alternativeFramings: [],
    confidenceGaps: [],
  };

  // What cannot be resolved
  if (!capabilities.hasOriginalLanguages) {
    critique.cannotResolve.push(
      'Morphological analysis of Hebrew/Greek roots (document lacks original languages)'
    );
  }

  if (!capabilities.hasCriticalApparatus) {
    critique.cannotResolve.push(
      'Full manuscript variant comparison (document lacks critical apparatus)'
    );
  }

  if (capabilities.hasTextualVariants && !capabilities.hasCriticalApparatus) {
    critique.cannotResolve.push(
      'Exhaustive variant enumeration (only editorial selections visible)'
    );
  }

  // Assumptions made
  if (query.toLowerCase().includes('bible') ||
      query.toLowerCase().includes('testament') ||
      query.toLowerCase().includes('genesis') ||
      query.toLowerCase().includes('john')) {
    critique.assumptionsMade.push(
      'Christian canonical frame assumed (Protestant 66-book canon based on document structure)'
    );
    critique.canonicalBias = 'Christian NT-inclusive reading';
  }

  if (query.toLowerCase().includes('tension') ||
      query.toLowerCase().includes('contradiction')) {
    critique.assumptionsMade.push(
      'Tensional reading assumed (harmonization is equally valid hermeneutic)'
    );
  }

  // Alternative framings
  critique.alternativeFramings.push(
    'Jewish reading: Proverbs 8 without christological lens',
    'Documentary hypothesis: Multiple authorship, no unified "biblical" agent',
    'Intertextual: Wisdom tradition as independent from Logos tradition'
  );

  // Confidence gaps
  if (claimsAnalyzed > 5) {
    critique.confidenceGaps.push(
      'Multiple claims analyzed; individual confidence may vary significantly'
    );
  }

  if (!capabilities.hasOriginalLanguages) {
    critique.confidenceGaps.push(
      'All semantic claims are translation-mediated; original sense inaccessible'
    );
  }

  return critique;
}

// ============================================================================
// INDETERMINACY LEVELS
// ============================================================================

export type IndeterminacyLevel = 'high' | 'medium' | 'low';

export interface IndeterminacyAssessment {
  level: IndeterminacyLevel;
  factors: string[];
  resolutionRequires: string[];
}

export function assessIndeterminacy(
  textualVariantsPresent: boolean,
  originalLanguagePresent: boolean,
  interpretiveOptionsCount: number
): IndeterminacyAssessment {
  const factors: string[] = [];
  const resolutionRequires: string[] = [];
  let score = 0;

  // Textual variants increase indeterminacy
  if (textualVariantsPresent) {
    factors.push('Multiple manuscript readings exist');
    resolutionRequires.push('Text-critical decision');
    score += 2;
  }

  // Lack of original language increases indeterminacy
  if (!originalLanguagePresent) {
    factors.push('Original language not available for verification');
    resolutionRequires.push('Access to Hebrew/Greek/Aramaic text');
    score += 2;
  }

  // Multiple interpretive options increase indeterminacy
  if (interpretiveOptionsCount >= 3) {
    factors.push(`${interpretiveOptionsCount} competing interpretations identified`);
    resolutionRequires.push('Hermeneutical decision');
    score += interpretiveOptionsCount - 2;
  }

  let level: IndeterminacyLevel;
  if (score >= 4) {
    level = 'high';
  } else if (score >= 2) {
    level = 'medium';
  } else {
    level = 'low';
  }

  return { level, factors, resolutionRequires };
}

// ============================================================================
// CONFIDENCE DECAY
// ============================================================================

export interface ConfidenceDecay {
  baseConfidence: number;  // 0-1
  decayFactors: { factor: string; penalty: number }[];
  finalConfidence: number;
  confidenceLevel: 'high' | 'medium' | 'low';
}

/**
 * Calculate confidence decay with CONSERVATIVE adjustments.
 * Critique: Previous 0.55 was inflated; target range 0.45-0.50 for typical queries.
 *
 * Key changes:
 * - Higher base penalties for non-direct sources
 * - Additional penalty for theological inference
 * - Stricter thresholds for confidence levels
 */
export function calculateConfidenceDecay(
  isDirectQuote: boolean,
  hasOriginalLanguage: boolean,
  inferenceDepth: number,
  hasExternalKnowledge: boolean,
  additionalPenalties?: { factor: string; penalty: number }[]
): ConfidenceDecay {
  let base = 1.0;
  const factors: { factor: string; penalty: number }[] = [];

  // Direct quote vs. paraphrase (INCREASED from 0.15)
  if (!isDirectQuote) {
    factors.push({ factor: 'Not a direct quote', penalty: 0.18 });
    base -= 0.18;
  }

  // Original language availability (INCREASED from 0.20)
  if (!hasOriginalLanguage) {
    factors.push({ factor: 'Translation-mediated (no original)', penalty: 0.25 });
    base -= 0.25;
  }

  // Inference depth penalty (INCREASED from 0.10)
  if (inferenceDepth > 0) {
    const penalty = inferenceDepth * 0.12;
    factors.push({ factor: `Inference depth: ${inferenceDepth}`, penalty });
    base -= penalty;
  }

  // External knowledge penalty (INCREASED from 0.25)
  if (hasExternalKnowledge) {
    factors.push({ factor: 'Relies on external knowledge', penalty: 0.28 });
    base -= 0.28;
  }

  // Apply additional penalties (temple theology, philosophical inference, etc.)
  if (additionalPenalties) {
    for (const { factor, penalty } of additionalPenalties) {
      factors.push({ factor, penalty });
      base -= penalty;
    }
  }

  // NEW: Baseline skepticism penalty for interpretive claims
  // This ensures typical theological queries land around 0.45-0.50
  factors.push({ factor: 'Baseline interpretive uncertainty', penalty: 0.05 });
  base -= 0.05;

  const finalConfidence = Math.max(0, base);

  // STRICTER thresholds (was 0.7/0.4)
  let confidenceLevel: 'high' | 'medium' | 'low';
  if (finalConfidence >= 0.75) {
    confidenceLevel = 'high';
  } else if (finalConfidence >= 0.45) {
    confidenceLevel = 'medium';
  } else {
    confidenceLevel = 'low';
  }

  return {
    baseConfidence: 1.0,
    decayFactors: factors,
    finalConfidence,
    confidenceLevel,
  };
}

// ============================================================================
// CANONICAL FRAME DETECTION
// ============================================================================

export interface CanonicalFrame {
  detected: string;
  alternatives: string[];
  warning: string;
}

export function detectCanonicalFrame(query: string, documentTitle: string): CanonicalFrame {
  const lowerQuery = query.toLowerCase();
  const lowerTitle = documentTitle.toLowerCase();

  // Detect Christian frame
  if (lowerTitle.includes('bible') ||
      lowerQuery.includes('new testament') ||
      lowerQuery.includes('logos') ||
      lowerQuery.includes('john 1')) {
    return {
      detected: 'Christian (Protestant 66-book canon)',
      alternatives: [
        'Jewish Tanakh (no NT, different order)',
        'Catholic (73 books, includes deuterocanon)',
        'Orthodox (varies, may include more books)',
        'Academic/secular (no canonical assumptions)',
      ],
      warning: 'Analysis presupposes Christian canonical frame. ' +
        'Same texts read differently in Jewish or academic contexts.',
    };
  }

  // Detect Jewish frame
  if (lowerQuery.includes('tanakh') ||
      lowerQuery.includes('torah') ||
      (lowerQuery.includes('wisdom') && !lowerQuery.includes('logos'))) {
    return {
      detected: 'Jewish (Tanakh)',
      alternatives: [
        'Christian OT (same books, different order and interpretation)',
        'Academic/secular',
      ],
      warning: 'Analysis uses Jewish canonical frame. ' +
        'Christological readings are external impositions.',
    };
  }

  // Default: academic
  return {
    detected: 'Academic/secular (no canonical assumptions)',
    alternatives: ['Christian', 'Jewish', 'Comparative religion'],
    warning: 'No specific canonical frame assumed.',
  };
}

// ============================================================================
// COMPLETE EPISTEMOLOGICAL REPORT
// ============================================================================

export interface EpistemologicalReport {
  documentId: number;
  documentTitle: string;
  capabilities: SourceCapabilities;
  languageHardStops: LanguageHardStop[];
  canonicalFrame: CanonicalFrame;
  autoCritique: AutoCritique;
  globalConfidence: ConfidenceDecay;
  templeTheologyPenalty: TempleTheologyPenalty;
  philosophicalInferences: PhilosophicalInference[];
  recommendations: string[];
}

export async function generateEpistemologicalReport(
  db: Database.Database,
  documentId: number,
  query: string,
  logger: Logger
): Promise<EpistemologicalReport> {
  const capabilities = await analyzeSourceCapabilities(db, documentId, logger);
  const hardStops = getLanguageHardStops(capabilities);
  const canonicalFrame = detectCanonicalFrame(query, capabilities.documentTitle);
  const autoCritique = generateAutoCritique(query, capabilities, 0);

  // NEW: Detect temple theology assumptions
  const templeTheologyPenalty = detectTempleTheologyPenalty('', query);

  // NEW: Detect philosophical inferences in query
  const philosophicalInferences = detectPhilosophicalInferences(query);

  // Calculate additional penalties from new detections
  const additionalPenalties: { factor: string; penalty: number }[] = [];

  if (templeTheologyPenalty.detected && !templeTheologyPenalty.hasExplicitPassage) {
    additionalPenalties.push({
      factor: `Temple theology without passage: ${templeTheologyPenalty.concepts.join(', ')}`,
      penalty: templeTheologyPenalty.penalty,
    });
  }

  for (const inference of philosophicalInferences) {
    additionalPenalties.push({
      factor: `Philosophical inference: ${inference.claim}`,
      penalty: inference.confidenceReduction,
    });
  }

  // Calculate confidence with new conservative formula + additional penalties
  const globalConfidence = calculateConfidenceDecay(
    false,  // Assume not all claims are direct quotes
    capabilities.hasOriginalLanguages,
    2,  // Assume moderate inference depth
    true,  // Assume some external knowledge used
    additionalPenalties
  );

  const recommendations: string[] = [];

  // Generate recommendations based on analysis
  if (!capabilities.hasOriginalLanguages) {
    recommendations.push(
      'RECOMMENDATION: Do not perform morphological analysis. Use translation-level observations only.'
    );
  }

  if (hardStops.some(s => s.blockedOperations.length > 0)) {
    recommendations.push(
      'RECOMMENDATION: Use [EXT] tag for any original language claims. Mark as requiring external verification.'
    );
  }

  if (canonicalFrame.detected.includes('Christian')) {
    recommendations.push(
      'RECOMMENDATION: Acknowledge Christian canonical frame explicitly. Note alternative readings exist.'
    );
  }

  // NEW: Temple theology recommendations
  if (templeTheologyPenalty.detected && !templeTheologyPenalty.hasExplicitPassage) {
    recommendations.push(
      `RECOMMENDATION: Temple theology invoked (${templeTheologyPenalty.concepts.join(', ')}). ` +
      `Ground with explicit passages: ${templeTheologyPenalty.requiredGrounding.slice(0, 3).join(', ')}.`
    );
  }

  // NEW: Philosophical inference recommendations
  if (philosophicalInferences.length > 0) {
    recommendations.push(
      `RECOMMENDATION: ${philosophicalInferences.length} philosophical/theological inference(s) detected. ` +
      `Mark each with [INFERENCE] tag and provide textual anchor if available.`
    );
  }

  recommendations.push(
    'RECOMMENDATION: Include auto-critique section acknowledging what cannot be resolved from this corpus.'
  );

  return {
    documentId,
    documentTitle: capabilities.documentTitle,
    capabilities,
    languageHardStops: hardStops,
    canonicalFrame,
    autoCritique,
    globalConfidence,
    templeTheologyPenalty,
    philosophicalInferences,
    recommendations,
  };
}

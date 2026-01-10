import Database from 'better-sqlite3';
import { Logger } from '../utils/logger.js';
import { getSegmentById } from '../db/queries/segments.js';

/**
 * Semantic Frames Module
 *
 * Detects conceptual frameworks in biblical/philosophical texts to prevent
 * reductive analysis. Distinguishes between causal, revelational, performative,
 * and invocative frames.
 */

// ============================================================================
// SEMANTIC FRAME TYPES
// ============================================================================

export type SemanticFrame =
  | 'causal'           // Efficient/instrumental cause (Aristotelian)
  | 'revelational'     // Light, life, manifestation (Johannine)
  | 'performative'     // Speech act that constitutes reality (Genesis)
  | 'invocative'       // Name-calling that makes present (Shem)
  | 'participatory'    // Being-in, dwelling (Pauline "in Christ")
  | 'unknown';

// ============================================================================
// INVOCATION TAXONOMY (Critique: "Name invocation = presence activation" too closed)
// ============================================================================

/**
 * Invocation levels from minimal to maximal presence claim.
 * Prevents collapsing all name-invocation into "ontological presence".
 */
export type InvocationLevel =
  | 'appeal'              // Minimal: calling upon, request (Psalms petition)
  | 'alignment'           // Identification with: "in the name of" as authorization
  | 'delegated_presence'  // Representative presence: messenger speaks FOR sender
  | 'ontological_presence' // Maximal: Name IS the presence itself (requires strong evidence)
  | 'indeterminate';      // Text does not resolve level

export interface InvocationAnalysis {
  level: InvocationLevel;
  confidence: number;  // 0-1, how certain we are of this level
  textualBasis: string[];  // Exact phrases supporting this level
  escalationRisk: string | null;  // Warning if claiming higher level than text supports
  alternatives: InvocationLevel[];  // Other valid readings
}

export interface FrameDetection {
  primaryFrame: SemanticFrame;
  secondaryFrames: SemanticFrame[];
  markers: FrameMarker[];
  warnings: string[];
  reductionRisk: string | null;
}

export interface FrameMarker {
  term: string;
  frame: SemanticFrame;
  context: string;
  significance: string;
}

// ============================================================================
// FRAME DETECTION PATTERNS
// ============================================================================

const FRAME_PATTERNS: Record<SemanticFrame, RegExp[]> = {
  causal: [
    /\b(through|by means of|created|made|caused|produced)\b/i,
    /\b(dia|di'|δια|δι')\b/i,  // Greek "through"
    /\b(efficient|instrumental|cause|agent)\b/i,
  ],
  revelational: [
    /\b(light|life|glory|radiance|manifest|reveal|shine)\b/i,
    /\b(φῶς|ζωή|δόξα|φανερόω)\b/i,  // Greek terms
    /\b(phos|zoe|doxa)\b/i,  // Transliterations
    /\b(image|likeness|representation|exact)\b/i,
  ],
  performative: [
    /\b(said|spoke|commanded|called|named)\b/i,
    /\b(and it was so|let there be|there was)\b/i,
    /\b(word of the lord came)\b/i,
    /\b(dabar|logos|rhema)\b/i,
  ],
  invocative: [
    /\b(name|called upon|invoke|proclaim)\b/i,
    /\b(shem|onoma|ὄνομα)\b/i,
    /\b(in the name of|by the name)\b/i,
    /\b(I AM|YHWH|Yahweh|Lord)\b/i,
  ],
  participatory: [
    /\b(in him|in christ|in whom|through whom|with him)\b/i,
    /\b(dwell|abide|remain|live in)\b/i,
    /\b(ἐν αὐτῷ|en auto)\b/i,
    /\b(fellowship|communion|partake)\b/i,
  ],
  unknown: [],
};

// Invocation level patterns (ordered from minimal to maximal)
const INVOCATION_PATTERNS: { level: InvocationLevel; patterns: RegExp[]; weight: number }[] = [
  {
    level: 'appeal',
    patterns: [
      /\b(call(?:ed|ing)? (?:upon|on|to)|cry(?:ing)? out|petition|pray(?:ed|ing)?)\b/i,
      /\b(hear me|answer me|save me|help me)\b/i,
      /\bO (Lord|God|YHWH)\b/i,
    ],
    weight: 0.25,
  },
  {
    level: 'alignment',
    patterns: [
      /\bin the name of\b(?!.*\b(presence|dwell|appear))/i,
      /\bby the name of\b/i,
      /\bfor (?:his|my|your) name'?s sake\b/i,
      /\bauthori(?:ty|zed)\b.*\bname\b/i,
    ],
    weight: 0.45,
  },
  {
    level: 'delegated_presence',
    patterns: [
      /\bangel of (?:the )?(?:Lord|YHWH)\b/i,
      /\bmessenger.*speak(?:s|ing)?\b/i,
      /\bsent in (?:the )?name\b/i,
      /\brepresent(?:s|ing)?\b.*\bpresence\b/i,
    ],
    weight: 0.65,
  },
  {
    level: 'ontological_presence',
    patterns: [
      /\bname\b.*\b(is|was)\b.*\b(there|present|dwell(?:s|ing)?)\b/i,
      /\bwhere(?:ver)? my name\b.*\b(come|appear|be)\b/i,
      /\bI AM\b.*\bname\b/i,
      /\bname\b.*\bforever\b.*\b(dwell|presence)\b/i,
    ],
    weight: 0.85,
  },
];

/**
 * Analyze invocation level with intermediate gradations.
 * Prevents escalating to "ontological presence" without textual support.
 */
export function analyzeInvocationLevel(content: string): InvocationAnalysis {
  const matches: { level: InvocationLevel; phrase: string; weight: number }[] = [];

  for (const { level, patterns, weight } of INVOCATION_PATTERNS) {
    for (const pattern of patterns) {
      const match = content.match(pattern);
      if (match) {
        matches.push({ level, phrase: match[0], weight });
      }
    }
  }

  if (matches.length === 0) {
    return {
      level: 'indeterminate',
      confidence: 0,
      textualBasis: [],
      escalationRisk: null,
      alternatives: ['appeal', 'alignment', 'delegated_presence', 'ontological_presence'],
    };
  }

  // Sort by weight, take highest supported level
  matches.sort((a, b) => b.weight - a.weight);
  const highestMatch = matches[0];

  // Collect all textual bases
  const textualBasis = matches.map(m => m.phrase);

  // Calculate confidence based on evidence strength
  const hasMultipleSupports = matches.filter(m => m.level === highestMatch.level).length > 1;
  const confidence = hasMultipleSupports ? Math.min(highestMatch.weight + 0.1, 0.9) : highestMatch.weight;

  // Identify alternatives (levels with some support)
  const supportedLevels = new Set(matches.map(m => m.level));
  const alternatives = Array.from(supportedLevels).filter(l => l !== highestMatch.level) as InvocationLevel[];

  // Escalation risk warning
  let escalationRisk: string | null = null;
  if (highestMatch.level === 'ontological_presence' && confidence < 0.7) {
    escalationRisk = 'ESCALATION RISK: Claiming ontological presence with limited textual support. ' +
      'Consider delegated_presence or alignment as safer interpretations.';
  } else if (highestMatch.level === 'delegated_presence' && alternatives.includes('alignment')) {
    escalationRisk = 'ESCALATION RISK: Text supports both delegated_presence and alignment. ' +
      'Lower level (alignment) may be more defensible.';
  }

  return {
    level: highestMatch.level,
    confidence,
    textualBasis,
    escalationRisk,
    alternatives,
  };
}

// Terms that indicate we should NOT reduce to causal frame
const NON_CAUSAL_INDICATORS = [
  { term: 'life', frame: 'revelational' as SemanticFrame, reason: 'Logos IS life, not produces life' },
  { term: 'light', frame: 'revelational' as SemanticFrame, reason: 'Logos IS light, not creates light' },
  { term: 'ζωή', frame: 'revelational' as SemanticFrame, reason: 'Greek life = ontological state, not effect' },
  { term: 'φῶς', frame: 'revelational' as SemanticFrame, reason: 'Greek light = condition of intelligibility' },
  { term: 'name', frame: 'invocative' as SemanticFrame, reason: 'Name = presence, not description' },
  { term: 'shem', frame: 'invocative' as SemanticFrame, reason: 'Hebrew Name = operative, not referential' },
  { term: 'said', frame: 'performative' as SemanticFrame, reason: 'Divine speech = constitutive act' },
  { term: 'spoke', frame: 'performative' as SemanticFrame, reason: 'Divine speech = reality-making' },
];

// ============================================================================
// SUBDETERMINATION ANALYSIS
// ============================================================================

export interface SubdeterminationAnalysis {
  textCloses: string[];      // What the text definitively excludes
  textLeaves: string[];      // What the text leaves open
  asymmetries: string[];     // Directional constraints in the text
  isDirected: boolean;       // Subdetermination vs. total indeterminacy
}

const ASYMMETRY_PATTERNS = [
  {
    pattern: /\bwas with\b.*\bgod\b/i,
    asymmetry: 'Logos oriented TOWARD God, not reverse',
    closes: 'Logos as independent origin',
  },
  {
    pattern: /\bπρὸς τὸν θεόν\b|pros ton theon/i,
    asymmetry: 'Greek pros = directional relation toward',
    closes: 'Symmetric co-equality without relation',
  },
  {
    pattern: /\bthrough him\b.*\ball things\b/i,
    asymmetry: 'Agent is mediated, not ultimate',
    closes: 'Logos as first cause (arche)',
  },
  {
    pattern: /\bfirstborn\b.*\bcreation\b/i,
    asymmetry: 'Temporal/logical priority, but within relation',
    closes: 'Neither pure creature nor pure creator',
  },
  {
    pattern: /\bradiance\b.*\bglory\b/i,
    asymmetry: 'Radiance implies source; glory implies origin',
    closes: 'Self-originating light',
  },
];

export function analyzeSubdetermination(content: string): SubdeterminationAnalysis {
  const analysis: SubdeterminationAnalysis = {
    textCloses: [],
    textLeaves: [],
    asymmetries: [],
    isDirected: false,
  };

  // Check for asymmetry patterns
  for (const { pattern, asymmetry, closes } of ASYMMETRY_PATTERNS) {
    if (pattern.test(content)) {
      analysis.asymmetries.push(asymmetry);
      analysis.textCloses.push(closes);
    }
  }

  // If we found asymmetries, subdetermination is directed
  analysis.isDirected = analysis.asymmetries.length > 0;

  // Common things left open in biblical texts
  if (content.match(/\bthrough\b/i)) {
    analysis.textLeaves.push('Whether "through" = instrumental or constitutive');
  }
  if (content.match(/\bmade\b|\bcreated\b/i)) {
    analysis.textLeaves.push('Whether agent is efficient cause or participatory');
  }
  if (content.match(/\bword\b|\blogos\b/i)) {
    analysis.textLeaves.push('Whether Word is attribute, hypostasis, or mode');
  }

  return analysis;
}

// ============================================================================
// PERFORMATIVE SPEECH ACT DETECTION
// ============================================================================

export interface PerformativeAnalysis {
  isPerformative: boolean;
  speechActs: SpeechAct[];
  constitutiveFormula: string | null;
  warning: string | null;
}

export interface SpeechAct {
  type: 'declarative' | 'imperative' | 'constitutive' | 'invocative';
  formula: string;
  effect: string;
}

const PERFORMATIVE_PATTERNS = [
  {
    pattern: /\b(god|lord)\s+said[,:]?\s*["']?let there be\b/i,
    type: 'constitutive' as const,
    effect: 'Speaking = Creating (no intermediation)',
  },
  {
    pattern: /\band it was so\b/i,
    type: 'constitutive' as const,
    effect: 'Speech act completed; reality altered',
  },
  {
    pattern: /\bcalled\s+(the\s+)?(\w+)\s+["']?(\w+)["']?/i,
    type: 'constitutive' as const,
    effect: 'Naming = ontological determination',
  },
  {
    pattern: /\bin the name of\b/i,
    type: 'invocative' as const,
    effect: 'Name invocation = presence activation',
  },
  {
    pattern: /\bthe word of the lord came\b/i,
    type: 'declarative' as const,
    effect: 'Divine speech as event, not report',
  },
];

export function analyzePerformatives(content: string): PerformativeAnalysis {
  const analysis: PerformativeAnalysis = {
    isPerformative: false,
    speechActs: [],
    constitutiveFormula: null,
    warning: null,
  };

  for (const { pattern, type, effect } of PERFORMATIVE_PATTERNS) {
    const match = content.match(pattern);
    if (match) {
      analysis.isPerformative = true;
      analysis.speechActs.push({
        type,
        formula: match[0],
        effect,
      });

      if (type === 'constitutive' && !analysis.constitutiveFormula) {
        analysis.constitutiveFormula = match[0];
      }
    }
  }

  if (analysis.isPerformative) {
    analysis.warning =
      'PERFORMATIVE DETECTED: Do not analyze as causal mechanism. ' +
      'Divine speech in this context IS the creative act, not a tool for it.';
  }

  return analysis;
}

// ============================================================================
// ANACHRONISM DETECTION
// ============================================================================

export interface AnachronismWarning {
  concept: string;
  origin: string;
  textPredates: boolean;
  warning: string;
  alternative: string;
}

const ANACHRONISTIC_CONCEPTS = [
  {
    pattern: /\b(efficient cause|instrumental cause|formal cause|final cause)\b/i,
    concept: 'Aristotelian four causes',
    origin: 'Aristotle, 4th century BCE',
    alternative: 'Hebrew verbal aspect (completed/ongoing action)',
  },
  {
    pattern: /\b(substance|essence|hypostasis|ousia)\b/i,
    concept: 'Greek metaphysical substance',
    origin: 'Platonic/Aristotelian tradition',
    alternative: 'Hebrew relational categories (covenant, presence)',
  },
  {
    pattern: /\b(trinity|trinitarian|three persons)\b/i,
    concept: 'Trinitarian doctrine',
    origin: 'Councils of Nicaea/Constantinople, 4th century CE',
    alternative: 'Text-internal relational language only',
  },
  {
    pattern: /\b(emanation|procession|generation)\b/i,
    concept: 'Neoplatonic emanationism',
    origin: 'Plotinus, 3rd century CE',
    alternative: 'Biblical creation/speech categories',
  },
  {
    pattern: /\b(logos|word)\b.*\b(reason|rationality|cosmic order)\b/i,
    concept: 'Stoic Logos doctrine',
    origin: 'Stoic philosophy, 3rd century BCE',
    alternative: 'Hebrew dabar (word-event)',
  },
];

export function detectAnachronisms(query: string): AnachronismWarning[] {
  const warnings: AnachronismWarning[] = [];

  for (const { pattern, concept, origin, alternative } of ANACHRONISTIC_CONCEPTS) {
    if (pattern.test(query)) {
      warnings.push({
        concept,
        origin,
        textPredates: true,
        warning: `ANACHRONISM WARNING: "${concept}" is a post-biblical category (${origin}). ` +
          `Applying it to biblical text imports external framework.`,
        alternative,
      });
    }
  }

  return warnings;
}

// ============================================================================
// MAIN FRAME DETECTION FUNCTION
// ============================================================================

export function detectSemanticFrames(content: string, query: string): FrameDetection {
  const detection: FrameDetection = {
    primaryFrame: 'unknown',
    secondaryFrames: [],
    markers: [],
    warnings: [],
    reductionRisk: null,
  };

  const frameCounts: Record<SemanticFrame, number> = {
    causal: 0,
    revelational: 0,
    performative: 0,
    invocative: 0,
    participatory: 0,
    unknown: 0,
  };

  // Detect frame markers in content
  for (const [frame, patterns] of Object.entries(FRAME_PATTERNS)) {
    for (const pattern of patterns) {
      const matches = content.match(new RegExp(pattern, 'gi'));
      if (matches) {
        frameCounts[frame as SemanticFrame] += matches.length;
        for (const match of matches.slice(0, 3)) {  // Limit markers
          detection.markers.push({
            term: match,
            frame: frame as SemanticFrame,
            context: getContext(content, match),
            significance: getSignificance(frame as SemanticFrame),
          });
        }
      }
    }
  }

  // Determine primary and secondary frames
  const sortedFrames = Object.entries(frameCounts)
    .filter(([f]) => f !== 'unknown')
    .sort((a, b) => b[1] - a[1]);

  if (sortedFrames.length > 0 && sortedFrames[0][1] > 0) {
    detection.primaryFrame = sortedFrames[0][0] as SemanticFrame;
    detection.secondaryFrames = sortedFrames
      .slice(1)
      .filter(([, count]) => count > 0)
      .map(([frame]) => frame as SemanticFrame);
  }

  // Check for non-causal indicators
  for (const { term, frame, reason } of NON_CAUSAL_INDICATORS) {
    if (content.toLowerCase().includes(term.toLowerCase())) {
      if (detection.primaryFrame === 'causal') {
        detection.warnings.push(
          `NON-CAUSAL INDICATOR: "${term}" suggests ${frame} frame. ${reason}`
        );
        detection.reductionRisk =
          `Text contains "${term}" which resists causal reduction. ` +
          `Consider ${frame} frame instead.`;
      }
    }
  }

  // Check for anachronisms in query
  const anachronisms = detectAnachronisms(query);
  for (const a of anachronisms) {
    detection.warnings.push(a.warning);
  }

  // Add reduction risk if causal frame dominant but others present
  if (detection.primaryFrame === 'causal' && detection.secondaryFrames.length > 0) {
    detection.reductionRisk =
      `Causal frame detected as primary, but ${detection.secondaryFrames.join(', ')} ` +
      `frames also present. Risk of reductive analysis.`;
  }

  return detection;
}

function getContext(content: string, term: string): string {
  const index = content.toLowerCase().indexOf(term.toLowerCase());
  if (index === -1) return '';
  const start = Math.max(0, index - 30);
  const end = Math.min(content.length, index + term.length + 30);
  return '...' + content.slice(start, end) + '...';
}

function getSignificance(frame: SemanticFrame): string {
  const significances: Record<SemanticFrame, string> = {
    causal: 'Suggests Aristotelian cause-effect analysis may be applicable',
    revelational: 'Indicates ontological identity (IS), not production (MAKES)',
    performative: 'Speech act that constitutes reality directly',
    invocative: 'Name-calling that makes present, not describes',
    participatory: 'Being-in relation, not external causation',
    unknown: 'Frame not determined',
  };
  return significances[frame];
}

// ============================================================================
// COMPLETE SEMANTIC ANALYSIS FOR A SEGMENT
// ============================================================================

export interface CompleteSemanticAnalysis {
  segmentId: number;
  frames: FrameDetection;
  subdetermination: SubdeterminationAnalysis;
  performatives: PerformativeAnalysis;
  invocation: InvocationAnalysis;  // NEW: Invocation level analysis
  anachronismWarnings: AnachronismWarning[];
  recommendation: string;
}

export async function analyzeSegmentSemantics(
  db: Database.Database,
  segmentId: number,
  query: string,
  logger: Logger
): Promise<CompleteSemanticAnalysis> {
  const segment = getSegmentById(db, segmentId);
  if (!segment) {
    throw new Error(`Segment ${segmentId} not found`);
  }

  const frames = detectSemanticFrames(segment.content, query);
  const subdetermination = analyzeSubdetermination(segment.content);
  const performatives = analyzePerformatives(segment.content);
  const invocation = analyzeInvocationLevel(segment.content);  // NEW
  const anachronismWarnings = detectAnachronisms(query);

  let recommendation = '';

  if (performatives.isPerformative) {
    recommendation = 'PERFORMATIVE: Analyze as speech-act, not causal mechanism. ';
  }

  if (frames.reductionRisk) {
    recommendation += `REDUCTION RISK: ${frames.reductionRisk} `;
  }

  if (subdetermination.isDirected) {
    recommendation += 'SUBDETERMINATION IS DIRECTED: Text closes some options. ';
    recommendation += `Closed: ${subdetermination.textCloses.join('; ')}. `;
  }

  // NEW: Add invocation level warnings
  if (invocation.escalationRisk) {
    recommendation += `INVOCATION: ${invocation.escalationRisk} `;
  }
  if (invocation.level !== 'indeterminate' && invocation.alternatives.length > 0) {
    recommendation += `Invocation level: ${invocation.level} (alternatives: ${invocation.alternatives.join(', ')}). `;
  }

  if (anachronismWarnings.length > 0) {
    recommendation += `ANACHRONISM: ${anachronismWarnings.length} post-biblical concepts detected in query. `;
  }

  logger.info('Semantic analysis complete', {
    segmentId,
    primaryFrame: frames.primaryFrame,
    isPerformative: performatives.isPerformative,
    isDirected: subdetermination.isDirected,
    invocationLevel: invocation.level,
  });

  return {
    segmentId,
    frames,
    subdetermination,
    performatives,
    invocation,
    anachronismWarnings,
    recommendation: recommendation || 'No special semantic considerations detected.',
  };
}

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import Database from 'better-sqlite3';
import { Logger } from '../utils/logger.js';
import { ErrorHandler } from '../utils/errors.js';
import { ingestDocument } from './ingest.js';
import { searchSegments } from './search.js';
import { getMetadata, getDocumentsList } from './metadata.js';
import { compareSegments } from './compare.js';
import {
  analyzeSourceCapabilities,
  validateClaim,
  generateDisclaimer,
} from './source-validation.js';
import {
  generateEpistemologicalReport,
  checkOperationAllowed,
  getLanguageHardStops,
} from './epistemological-guard.js';
import {
  detectSemanticFrames,
  analyzeSubdetermination,
  analyzePerformatives,
  detectAnachronisms,
  analyzeSegmentSemantics,
} from './semantic-frames.js';
import {
  runCognitiveAudit,
  detectInferentialConnectors,
  detectProhibitedAbstractions,
  buildDocumentVocabulary,
  validateOutputVocabulary,
  analyzeQueryIntent,
  generateSafeFallback,
  classifyTextType,
  type CognitiveAudit,
  type VocabularyControl,
} from './cognitive-constraints.js';
import {
  validateLiteralQuote,
  validateProximity,
  getAdjacentSegmentIds,
  identifySpeaker,
  validateSpeaker,
  detectPatternContamination,
  validateExtractionSchema,
  createExtractionSchema,
  detectNarrativeVoice,
  validateAgencyExecution,
  detectWeakQuantifiers,
  detectEvasionPatterns,
  validateExistentialResponse,
  generateExistentialFallback,
  // Speech vs Action verb classification (domain-agnostic)
  detectTextGenre,
  detectDivineAgencyWithoutSpeech,
  // Types for domain-agnostic configuration
  type DomainVocabulary,
} from './extraction-validators.js';

export interface ToolContext {
  db: Database.Database;
  errorHandler: ErrorHandler;
  logger: Logger;
}

const TOOLS = [
  {
    name: 'ingest_document',
    description: 'Load, segment, and index a document for search. Supports txt, md, pdf, epub, and html formats. Automatically detects chapters and sections.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        path: {
          type: 'string',
          description: 'Absolute path to the document file',
        },
        title: {
          type: 'string',
          description: 'Optional title for the document (defaults to filename)',
        },
        force: {
          type: 'boolean',
          description: 'Force re-indexing even if document already exists with same content',
          default: false,
        },
        chunkSize: {
          type: 'number',
          description: 'Target size in words for each chunk (default: 2000)',
          default: 2000,
        },
        overlap: {
          type: 'number',
          description: 'Number of words to overlap between chunks (default: 100)',
          default: 100,
        },
      },
      required: ['path'],
    },
  },
  {
    name: 'search_segment',
    description: 'Search for relevant segments within indexed documents using TF-IDF. Returns snippets with matched terms highlighted.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        query: {
          type: 'string',
          description: 'Search query (keywords or phrases)',
        },
        documentId: {
          type: 'number',
          description: 'Optional: limit search to a specific document',
        },
        segmentId: {
          type: 'number',
          description: 'Optional: search within a specific segment only',
        },
        limit: {
          type: 'number',
          description: 'Maximum number of results to return (default: 5)',
          default: 5,
        },
        contextWords: {
          type: 'number',
          description: 'Number of words to include around matches in snippets (default: 50)',
          default: 50,
        },
      },
      required: ['query'],
    },
  },
  {
    name: 'get_metadata',
    description: 'Get metadata, structure, and statistics for a document or segment. Includes top terms by TF-IDF.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        documentId: {
          type: 'number',
          description: 'ID of the document to get metadata for',
        },
        segmentId: {
          type: 'number',
          description: 'ID of the segment to get metadata for',
        },
        topTerms: {
          type: 'number',
          description: 'Number of top terms to return (default: 10)',
          default: 10,
        },
        includeStructure: {
          type: 'boolean',
          description: 'Include document structure (chapters/sections) in response',
          default: true,
        },
      },
    },
  },
  {
    name: 'compare_segments',
    description: 'Compare two segments to find shared themes, unique terms, and similarity score. Useful for understanding relationships between chapters.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        segmentIdA: {
          type: 'number',
          description: 'ID of the first segment to compare',
        },
        segmentIdB: {
          type: 'number',
          description: 'ID of the second segment to compare',
        },
        findBridges: {
          type: 'boolean',
          description: 'Find intermediate segments that connect the two (default: true)',
          default: true,
        },
        maxBridges: {
          type: 'number',
          description: 'Maximum number of bridge segments to return (default: 3)',
          default: 3,
        },
      },
      required: ['segmentIdA', 'segmentIdB'],
    },
  },
  {
    name: 'list_documents',
    description: 'List all indexed documents with their metadata',
    inputSchema: {
      type: 'object' as const,
      properties: {
        limit: {
          type: 'number',
          description: 'Maximum number of documents to return (default: 20)',
          default: 20,
        },
        offset: {
          type: 'number',
          description: 'Number of documents to skip (for pagination)',
          default: 0,
        },
      },
    },
  },
  {
    name: 'get_source_capabilities',
    description: 'CRITICAL: Analyze what a document CAN and CANNOT support for grounded claims. Returns detected languages, whether original Hebrew/Greek/Aramaic is present, textual variant availability, and epistemological limitations. MUST be called before making claims about morphology, etymology, or textual criticism.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        documentId: {
          type: 'number',
          description: 'ID of the document to analyze',
        },
      },
      required: ['documentId'],
    },
  },
  {
    name: 'validate_claim',
    description: 'Check if a specific claim can be grounded in the source document. Returns whether the claim requires capabilities the document lacks (e.g., original languages, textual variants, critical apparatus). Use this BEFORE making scholarly assertions.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        documentId: {
          type: 'number',
          description: 'ID of the document to validate against',
        },
        claim: {
          type: 'string',
          description: 'The claim or assertion to validate (e.g., "The Hebrew root QNH means...")',
        },
      },
      required: ['documentId', 'claim'],
    },
  },
  {
    name: 'get_epistemological_report',
    description: 'Generate a complete epistemological analysis before making scholarly claims. Returns: language hard stops, canonical frame detection, auto-critique of what cannot be resolved, confidence decay calculation, and specific recommendations. Use this BEFORE any complex textual analysis.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        documentId: {
          type: 'number',
          description: 'ID of the document to analyze',
        },
        query: {
          type: 'string',
          description: 'The research question or claim being investigated',
        },
      },
      required: ['documentId', 'query'],
    },
  },
  {
    name: 'check_language_operation',
    description: 'Check if a specific linguistic operation is allowed given the document capabilities. Use before performing morphological, etymological, or text-critical analysis.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        documentId: {
          type: 'number',
          description: 'ID of the document',
        },
        operation: {
          type: 'string',
          description: 'The operation to check (e.g., "root analysis", "manuscript comparison")',
        },
        language: {
          type: 'string',
          description: 'The language involved (hebrew, greek, aramaic)',
        },
      },
      required: ['documentId', 'operation', 'language'],
    },
  },
  {
    name: 'detect_semantic_frames',
    description: 'Detect conceptual frameworks (causal, revelational, performative, invocative) in a text segment. Prevents reductive analysis by identifying when text uses non-causal categories like life/light (Johannine) or speech-acts (Genesis).',
    inputSchema: {
      type: 'object' as const,
      properties: {
        segmentId: {
          type: 'number',
          description: 'ID of the segment to analyze',
        },
        query: {
          type: 'string',
          description: 'The research question being investigated (checked for anachronisms)',
        },
      },
      required: ['segmentId', 'query'],
    },
  },
  {
    name: 'analyze_subdetermination',
    description: 'Analyze whether textual ambiguity is total indeterminacy or directed subdetermination. Returns what the text CLOSES (excludes) vs. what it LEAVES OPEN, and detects asymmetric relations.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        segmentId: {
          type: 'number',
          description: 'ID of the segment to analyze',
        },
      },
      required: ['segmentId'],
    },
  },
  {
    name: 'detect_performatives',
    description: 'Detect performative speech acts where divine speech IS the creative act (not a tool for it). Identifies "And God said... and it was so" patterns that resist causal analysis.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        segmentId: {
          type: 'number',
          description: 'ID of the segment to analyze',
        },
      },
      required: ['segmentId'],
    },
  },
  {
    name: 'check_anachronisms',
    description: 'Check if a research question imports post-biblical conceptual categories (Aristotelian causes, Neoplatonic emanation, Trinitarian doctrine) that may distort text-internal meaning.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        query: {
          type: 'string',
          description: 'The research question or claim to check for anachronistic concepts',
        },
      },
      required: ['query'],
    },
  },
  // ============================================================================
  // COGNITIVE CONSTRAINT TOOLS (New)
  // ============================================================================
  {
    name: 'audit_cognitive_operations',
    description: 'CRITICAL: Run before ANY response. Validates that query and planned output comply with cognitive constraints. Detects unauthorized operations (synthesis, explanation, causality inference). Returns compliance status and safe fallback if needed.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        documentId: {
          type: 'number',
          description: 'ID of the document being queried',
        },
        query: {
          type: 'string',
          description: 'The user query to analyze for unauthorized operations',
        },
        plannedOutput: {
          type: 'string',
          description: 'The planned response text to validate before sending',
        },
      },
      required: ['documentId', 'query'],
    },
  },
  {
    name: 'validate_output_vocabulary',
    description: 'Check if output uses only vocabulary present in the source document. Detects terms imported from outside the text. Use after generating response.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        documentId: {
          type: 'number',
          description: 'ID of the document',
        },
        output: {
          type: 'string',
          description: 'The output text to validate against document vocabulary',
        },
      },
      required: ['documentId', 'output'],
    },
  },
  {
    name: 'detect_inference_violations',
    description: 'Scan text for inferential connectors (therefore, thus, implies, means that) and prohibited abstract nouns (ontology, mechanism, structure). These signal unauthorized cognitive operations.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        text: {
          type: 'string',
          description: 'The text to scan for inference violations',
        },
      },
      required: ['text'],
    },
  },
  {
    name: 'get_permitted_operations',
    description: 'Get list of permitted cognitive operations for a segment based on its text type (narrative, poetry, wisdom, prophecy, epistle, apocalyptic, law, genealogy). Different genres allow different operations.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        segmentId: {
          type: 'number',
          description: 'ID of the segment to check',
        },
      },
      required: ['segmentId'],
    },
  },
  {
    name: 'generate_safe_fallback',
    description: 'Generate a safe, compliant response when a query requires unauthorized operations. Use when audit_cognitive_operations returns violations.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        questionType: {
          type: 'string',
          enum: ['synthesis', 'explanation', 'causality', 'teleology', 'cross_section'],
          description: 'The type of unauthorized operation requested',
        },
        documentTitle: {
          type: 'string',
          description: 'Title of the document for the fallback message',
        },
      },
      required: ['questionType', 'documentTitle'],
    },
  },
  {
    name: 'build_document_vocabulary',
    description: 'Build closed vocabulary from document. Creates lexicon of all tokens in document. Required before using validate_output_vocabulary.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        documentId: {
          type: 'number',
          description: 'ID of the document to build vocabulary from',
        },
      },
      required: ['documentId'],
    },
  },
  // ============================================================================
  // EXTRACTION VALIDATION TOOLS (Prevent hallucination in extractions)
  // ============================================================================
  {
    name: 'validate_literal_quote',
    description: 'Verify that a quoted string exists EXACTLY in a segment or document. Use this BEFORE claiming any text appears in the source. Returns confidence: "textual" (exact match), "partial" (similar text found), or "not_found". Prevents pattern completion hallucination.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        quote: {
          type: 'string',
          description: 'The exact quote to validate',
        },
        segmentId: {
          type: 'number',
          description: 'Optional: specific segment to check',
        },
        documentId: {
          type: 'number',
          description: 'Optional: document to search (if no segmentId)',
        },
        fuzzyThreshold: {
          type: 'number',
          description: 'Similarity threshold for partial matches (0-1, default: 0.8)',
          default: 0.8,
        },
      },
      required: ['quote'],
    },
  },
  {
    name: 'validate_proximity',
    description: 'Check if two segments are adjacent (within allowed distance). Use to enforce "same verse or verse+1" constraints. Prevents narrative jump violations where content from distant sections is incorrectly associated.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        baseSegmentId: {
          type: 'number',
          description: 'The anchor segment ID (e.g., where speech occurs)',
        },
        targetSegmentId: {
          type: 'number',
          description: 'The segment ID being referenced for effect',
        },
        maxDistance: {
          type: 'number',
          description: 'Maximum allowed segment distance (0 = same segment, 1 = adjacent)',
          default: 1,
        },
      },
      required: ['baseSegmentId', 'targetSegmentId'],
    },
  },
  {
    name: 'get_adjacent_segments',
    description: 'Get list of segment IDs within proximity constraint of a base segment. Use for extraction queries that require adjacency.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        baseSegmentId: {
          type: 'number',
          description: 'The anchor segment ID',
        },
        maxDistance: {
          type: 'number',
          description: 'Maximum distance from base (default: 1)',
          default: 1,
        },
      },
      required: ['baseSegmentId'],
    },
  },
  {
    name: 'identify_speaker',
    description: 'Identify who is speaking in a text segment. Returns speaker name, confidence level (explicit/contextual/ambiguous/unknown), and evidence. Domain-agnostic: works for any document type (religious, academic, legal, literary).',
    inputSchema: {
      type: 'object' as const,
      properties: {
        segmentId: {
          type: 'number',
          description: 'ID of the segment to analyze',
        },
        expectedSpeaker: {
          type: 'string',
          description: 'Optional: verify this specific speaker is the agent',
        },
        priorityPatterns: {
          type: 'array',
          items: { type: 'string' },
          description: 'Optional: Speaker names to prioritize when multiple found. Agent constructs dynamically based on document context. Examples: ["God", "Lord"] for religious texts, ["Dr. Smith", "Professor"] for academic, ["Plaintiff", "Defendant"] for legal.',
        },
        excludePatterns: {
          type: 'array',
          items: { type: 'string' },
          description: 'Optional: Speaker patterns to flag as ambiguous/excluded. Agent constructs dynamically. Examples: ["angel of", "messenger"] for religious texts, ["assistant", "secretary"] for academic, ["witness"] for legal.',
        },
      },
      required: ['segmentId'],
    },
  },
  {
    name: 'detect_pattern_contamination',
    description: 'Detect when output may be completing a known pattern not in source. Domain-agnostic: works for any genre (religious, fairy tales, legal formulas, academic citations). Agent provides patterns dynamically based on document genre.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        claimedOutput: {
          type: 'string',
          description: 'What the agent claims is in the text',
        },
        segmentId: {
          type: 'number',
          description: 'ID of the segment to check against',
        },
        patterns: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              trigger: {
                type: 'string',
                description: 'Trigger phrase that starts the pattern',
              },
              expectedCompletion: {
                type: 'string',
                description: 'Common completion that might be hallucinated',
              },
              description: {
                type: 'string',
                description: 'Optional: Description of the pattern',
              },
            },
            required: ['trigger', 'expectedCompletion'],
          },
          description: 'Optional: Pattern definitions agent constructs based on document genre. Examples: Biblical [{trigger: "and God said", expectedCompletion: "and it was so"}], Fairy tale [{trigger: "once upon a time", expectedCompletion: "happily ever after"}], Legal [{trigger: "the court finds", expectedCompletion: "in favor of"}]. Leave empty for generic detection.',
        },
      },
      required: ['claimedOutput', 'segmentId'],
    },
  },
  {
    name: 'validate_extraction_schema',
    description: 'Validate that extraction output follows a strict schema without unauthorized commentary. Detects parenthetical comments, notes sections, evaluative language. Use when user requests pure data extraction.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        output: {
          type: 'string',
          description: 'The extraction output to validate',
        },
        fields: {
          type: 'array',
          items: { type: 'string' },
          description: 'Expected field names in output (e.g., ["Book", "Chapter", "Speech", "Effect"])',
        },
        allowCommentary: {
          type: 'boolean',
          description: 'Whether commentary is allowed (default: false)',
          default: false,
        },
      },
      required: ['output', 'fields'],
    },
  },
  // ============================================================================
  // NEW: NARRATIVE VOICE & AGENCY TOOLS
  // ============================================================================
  {
    name: 'detect_narrative_voice',
    description: 'DOMAIN-AGNOSTIC: Detect the narrative voice type of a text segment. Distinguishes: (1) primary_narration ("The agent did X") = action executed in-scene, (2) human_to_divine ("You led them...") = human prayer/praise, action RETROSPECTIVE not executed, (3) divine_direct_speech ("I am the X") = agent speaking, (4) human_about_divine ("The X is my shepherd") = descriptive. Use BEFORE extracting "actions" to avoid confusing retrospective prayer with primary agency.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        segmentId: {
          type: 'number',
          description: 'ID of the segment to analyze',
        },
        domainVocabulary: {
          type: 'object',
          description: 'Optional: Domain vocabulary for enhanced detection. Properties: agents (e.g., ["God", "Lord"]), addressees (e.g., ["Lord", "Your Honor"]), actionVerbs (e.g., ["led", "brought", "gave"]), narrationVerbs (e.g., ["said", "spoke", "did"]), stateVerbs (e.g., ["is", "was"]), oracleFormulas (e.g., ["thus says the Lord"]), praiseFormulas (e.g., ["praise the Lord"]).',
        },
      },
      required: ['segmentId'],
    },
  },
  {
    name: 'validate_agency_execution',
    description: 'DOMAIN-AGNOSTIC: Validates whether an action is EXECUTED in-scene vs merely REFERENCED retrospectively. Key distinction: EXECUTED = "Fire came up from the rock and consumed" (primary narration), REFERENCED = "You led them with a pillar of cloud" (retrospective prayer). The second describes same action but as human retrospective memory, NOT primary execution. Returns isExecuted boolean, mode (executed/retrospective/prospective/hypothetical), and warning if confused.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        segmentId: {
          type: 'number',
          description: 'ID of the segment to analyze',
        },
        agentPatterns: {
          type: 'array',
          items: { type: 'string' },
          description: 'Optional: Agent names to search for (e.g., ["God", "Lord"] for biblical, ["Allah"] for Quran, ["the Court"] for legal, ["the King"] for literary).',
        },
        domainVocabulary: {
          type: 'object',
          description: 'Optional: Domain vocabulary for comprehensive detection. Properties: agents, addressees, actionVerbs, narrationVerbs, stateVerbs, oracleFormulas, praiseFormulas.',
        },
      },
      required: ['segmentId'],
    },
  },
  {
    name: 'detect_weak_quantifiers',
    description: 'Detects weak quantifiers in text that require statistical evidence. Quantifiers like "frequently", "typically", "generally", "always", "never" imply statistical claims that should not be made without counting evidence. Returns recommendation: "allow", "require_count", or "block". Use on agent output BEFORE returning to user to catch unsupported generalizations.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        text: {
          type: 'string',
          description: 'Text to analyze (typically agent output before returning to user)',
        },
      },
      required: ['text'],
    },
  },
  // ============================================================================
  // NEW: EXISTENTIAL RESPONSE VALIDATION TOOLS
  // ============================================================================
  {
    name: 'detect_inference_violations',
    description: 'Scan text for inferential connectors (therefore, thus, implies, means that) and prohibited abstract nouns (ontology, mechanism, structure). These signal unauthorized cognitive operations.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        text: {
          type: 'string',
          description: 'The text to scan for inference violations',
        },
      },
      required: ['text'],
    },
  },
  {
    name: 'validate_existential_response',
    description: 'CRITICAL: Validates that a response to an existential question ("Does X exist in text?") meets the contract. VALID: "YES" + textual evidence, OR "NO" + explicit denial. INVALID: meta-discourse about limitations, hedging, asking follow-up questions, introducing categories not asked for. Use this AFTER generating response to existential questions to catch evasion.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        response: {
          type: 'string',
          description: 'The agent response to validate',
        },
      },
      required: ['response'],
    },
  },
  {
    name: 'generate_safe_fallback',
    description: 'Generate a safe, compliant response when a query requires unauthorized operations. Use when audit_cognitive_operations returns violations.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        questionType: {
          type: 'string',
          enum: ['synthesis', 'explanation', 'causality', 'teleology', 'cross_section'],
          description: 'The type of unauthorized operation requested',
        },
        documentTitle: {
          type: 'string',
          description: 'Title of the document for the fallback message',
        },
      },
      required: ['questionType', 'documentTitle'],
    },
  },
  // ============================================================================
  // NEW: SPEECH VS ACTION CLASSIFICATION & DIVINE AGENCY DETECTION
  // ============================================================================
  {
    name: 'detect_text_genre',
    description: 'Detect text genre (historical_narrative, narrative_poetry, prayer_praise, recapitulation, prophetic) to apply correct extraction rules. DOMAIN-AGNOSTIC: Uses structural patterns by default. Provide domainVocabulary for domain-specific enhanced detection.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        segmentId: {
          type: 'number',
          description: 'ID of the segment to analyze',
        },
        domainVocabulary: {
          type: 'object',
          description: 'Optional: Domain-specific vocabulary for enhanced detection. Agent constructs dynamically based on document context.',
          properties: {
            agents: {
              type: 'array',
              items: { type: 'string' },
              description: 'Primary agents/actors (e.g., ["God", "Lord"] for biblical, ["the Court"] for legal)',
            },
            addressees: {
              type: 'array',
              items: { type: 'string' },
              description: 'Terms for addressing authority (e.g., ["Lord", "God"] or ["Your Honor"])',
            },
            oracleFormulas: {
              type: 'array',
              items: { type: 'string' },
              description: 'Proclamation formulas (e.g., ["thus says the Lord"] or ["the Court finds"])',
            },
            praiseFormulas: {
              type: 'array',
              items: { type: 'string' },
              description: 'Praise/worship terms (e.g., ["praise the Lord"] or ["glory to Allah"])',
            },
          },
        },
      },
      required: ['segmentId'],
    },
  },
  {
    name: 'detect_divine_agency_without_speech',
    description: 'CRITICAL: Detect when an agent acts WITHOUT speaking. DOMAIN-AGNOSTIC: Agent provides agentPatterns dynamically. Separates SPEECH verbs (said, spoke, called) from ACTION verbs (caused, drove, made, remembered). Examples: Biblical ["God", "Lord"] finds "God remembered Noah", Legal ["the Court"] finds "the Court ruled".',
    inputSchema: {
      type: 'object' as const,
      properties: {
        segmentId: {
          type: 'number',
          description: 'ID of the segment to analyze',
        },
        agentPatterns: {
          type: 'array',
          items: { type: 'string' },
          description: 'Agent names to search for. Agent constructs dynamically: ["God", "Lord"] for biblical, ["Allah"] for Quran, ["the Court", "the Judge"] for legal, ["the King"] for literary. If not provided, detects action verbs only without agent attribution.',
        },
        domainVocabulary: {
          type: 'object',
          description: 'Optional: Domain vocabulary for genre detection (same structure as detect_text_genre).',
          properties: {
            agents: { type: 'array', items: { type: 'string' } },
            addressees: { type: 'array', items: { type: 'string' } },
            oracleFormulas: { type: 'array', items: { type: 'string' } },
            praiseFormulas: { type: 'array', items: { type: 'string' } },
          },
        },
      },
      required: ['segmentId'],
    },
  },
];

export async function registerTools(server: Server, context: ToolContext): Promise<void> {
  const { db, errorHandler, logger } = context;

  // Register list tools handler
  server.setRequestHandler(ListToolsRequestSchema, async () => {
    return { tools: TOOLS };
  });

  // Register call tool handler
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    logger.debug('Tool called', { name, args });

    try {
      let result: unknown;

      switch (name) {
        case 'ingest_document':
          result = await ingestDocument(db, args, logger, errorHandler);
          break;

        case 'search_segment':
          result = await searchSegments(db, args, logger, errorHandler);
          break;

        case 'get_metadata':
          result = await getMetadata(db, args, logger, errorHandler);
          break;

        case 'compare_segments':
          result = await compareSegments(db, args, logger, errorHandler);
          break;

        case 'list_documents':
          result = await getDocumentsList(db, args, logger, errorHandler);
          break;

        case 'get_source_capabilities': {
          const docId = (args as { documentId: number }).documentId;
          const capabilities = await analyzeSourceCapabilities(db, docId, logger);
          const disclaimer = generateDisclaimer(capabilities);
          result = {
            ...capabilities,
            disclaimer,
          };
          break;
        }

        case 'validate_claim': {
          const { documentId, claim } = args as { documentId: number; claim: string };
          const caps = await analyzeSourceCapabilities(db, documentId, logger);
          result = validateClaim(claim, caps);
          break;
        }

        case 'get_epistemological_report': {
          const { documentId, query } = args as { documentId: number; query: string };
          result = await generateEpistemologicalReport(db, documentId, query, logger);
          break;
        }

        case 'check_language_operation': {
          const { documentId, operation, language } = args as {
            documentId: number;
            operation: string;
            language: string;
          };
          const caps = await analyzeSourceCapabilities(db, documentId, logger);
          const hardStops = getLanguageHardStops(caps);
          result = checkOperationAllowed(operation, language, hardStops);
          break;
        }

        case 'detect_semantic_frames': {
          const { segmentId, query } = args as { segmentId: number; query: string };
          result = await analyzeSegmentSemantics(db, segmentId, query, logger);
          break;
        }

        case 'analyze_subdetermination': {
          const { segmentId } = args as { segmentId: number };
          const segment = await import('../db/queries/segments.js').then(m => m.getSegmentById(db, segmentId));
          if (!segment) throw errorHandler.createInvalidParamsError(`Segment ${segmentId} not found`);
          result = analyzeSubdetermination(segment.content);
          break;
        }

        case 'detect_performatives': {
          const { segmentId } = args as { segmentId: number };
          const segment = await import('../db/queries/segments.js').then(m => m.getSegmentById(db, segmentId));
          if (!segment) throw errorHandler.createInvalidParamsError(`Segment ${segmentId} not found`);
          result = analyzePerformatives(segment.content);
          break;
        }

        case 'check_anachronisms': {
          const { query } = args as { query: string };
          result = detectAnachronisms(query);
          break;
        }

        // ============================================================================
        // COGNITIVE CONSTRAINT HANDLERS
        // ============================================================================

        case 'audit_cognitive_operations': {
          const { documentId, query, plannedOutput } = args as {
            documentId: number;
            query: string;
            plannedOutput?: string;
          };

          // Build vocabulary if needed (cached in memory for session)
          const vocabulary = buildDocumentVocabulary(db, documentId, logger);

          // Run audit
          const audit = runCognitiveAudit(
            documentId,
            query,
            plannedOutput || '',
            vocabulary,
            undefined, // referencedSections - would need extraction
            undefined, // referencedBooks - would need extraction
            logger
          );

          result = {
            ...audit,
            // Add explicit guidance
            mustUse: audit.isCompliant ? null : audit.fallback?.safeResponse,
            operationsAllowed: ['quote', 'list', 'paraphrase', 'locate', 'compare_verses', 'count', 'extract'],
            operationsProhibited: ['synthesize', 'explain_why', 'abstract', 'cross_section_infer', 'causality_infer', 'teleology_infer'],
          };
          break;
        }

        case 'validate_output_vocabulary': {
          const { documentId, output } = args as { documentId: number; output: string };

          const vocabulary = buildDocumentVocabulary(db, documentId, logger);
          const validation = validateOutputVocabulary(output, vocabulary);

          result = {
            ...validation,
            vocabularySize: vocabulary.totalTokens,
            recommendation: validation.isCompliant
              ? 'Output uses document vocabulary correctly'
              : `Remove or replace these terms: ${validation.illegalTokens.slice(0, 10).join(', ')}`,
          };
          break;
        }

        case 'detect_inference_violations': {
          const { text } = args as { text: string };

          const connectors = detectInferentialConnectors(text);
          const abstractions = detectProhibitedAbstractions(text);

          result = {
            hasViolations: connectors.detected || abstractions.detected,
            inferentialConnectors: connectors,
            prohibitedAbstractions: abstractions,
            recommendation: (connectors.detected || abstractions.detected)
              ? 'VIOLATION: Remove inferential language and abstract terms. Use only quoting and listing.'
              : 'No inference violations detected',
          };
          break;
        }

        case 'get_permitted_operations': {
          const { segmentId } = args as { segmentId: number };
          const segment = await import('../db/queries/segments.js').then(m => m.getSegmentById(db, segmentId));
          if (!segment) throw errorHandler.createInvalidParamsError(`Segment ${segmentId} not found`);

          // Classify text type
          const textType = classifyTextType(segment.content, segment.title || '');

          // Import operations map
          const { OPERATIONS_BY_TEXT_TYPE } = await import('./cognitive-constraints.js');
          const permitted = OPERATIONS_BY_TEXT_TYPE[textType];

          result = {
            segmentId,
            textType,
            permittedOperations: permitted,
            prohibitedOperations: ['synthesize', 'explain_why', 'abstract', 'cross_section_infer', 'causality_infer', 'teleology_infer'],
            warning: textType === 'apocalyptic'
              ? 'APOCALYPTIC TEXT: Heavily restricted operations. Only quote and list permitted.'
              : textType === 'poetry'
              ? 'POETRY: Paraphrase not recommended. Quote directly.'
              : null,
          };
          break;
        }

        case 'generate_safe_fallback': {
          const { questionType, documentTitle } = args as {
            questionType: 'synthesis' | 'explanation' | 'causality' | 'teleology' | 'cross_section';
            documentTitle: string;
          };

          const fallback = generateSafeFallback(questionType, documentTitle);
          result = fallback;
          break;
        }

        case 'build_document_vocabulary': {
          const { documentId } = args as { documentId: number };

          const vocabulary = buildDocumentVocabulary(db, documentId, logger);

          // Optionally persist to database
          const insertStmt = db.prepare(`
            INSERT OR REPLACE INTO document_vocabulary (document_id, token, frequency)
            VALUES (?, ?, 1)
          `);

          const insertMany = db.transaction((tokens: string[]) => {
            for (const token of tokens) {
              insertStmt.run(documentId, token);
            }
          });

          const tokenArray = Array.from(vocabulary.allowedTokens);
          insertMany(tokenArray);

          // Update metadata
          db.prepare(`
            INSERT OR REPLACE INTO document_metadata (document_id, vocabulary_size, vocabulary_built_at)
            VALUES (?, ?, datetime('now'))
          `).run(documentId, vocabulary.totalTokens);

          result = {
            documentId,
            vocabularySize: vocabulary.totalTokens,
            sampleTokens: tokenArray.slice(0, 50),
            message: 'Vocabulary built and persisted. validate_output_vocabulary now available.',
          };
          break;
        }

        // ============================================================================
        // EXTRACTION VALIDATION HANDLERS
        // ============================================================================

        case 'validate_literal_quote': {
          const { quote, segmentId, documentId, fuzzyThreshold } = args as {
            quote: string;
            segmentId?: number;
            documentId?: number;
            fuzzyThreshold?: number;
          };

          if (!segmentId && !documentId) {
            throw errorHandler.createInvalidParamsError('Must provide either segmentId or documentId');
          }

          result = validateLiteralQuote(db, quote, segmentId, documentId, fuzzyThreshold ?? 0.8, logger);
          break;
        }

        case 'validate_proximity': {
          const { baseSegmentId, targetSegmentId, maxDistance } = args as {
            baseSegmentId: number;
            targetSegmentId: number;
            maxDistance?: number;
          };

          result = validateProximity(db, baseSegmentId, targetSegmentId, maxDistance ?? 1, logger);
          break;
        }

        case 'get_adjacent_segments': {
          const { baseSegmentId, maxDistance } = args as {
            baseSegmentId: number;
            maxDistance?: number;
          };

          const adjacentIds = getAdjacentSegmentIds(db, baseSegmentId, maxDistance ?? 1, logger);

          // Fetch segment info for context
          const segments = db.prepare(`
            SELECT id, title, position, word_count FROM segments WHERE id IN (${adjacentIds.map(() => '?').join(',')})
            ORDER BY position
          `).all(...adjacentIds) as { id: number; title: string; position: number; word_count: number }[];

          result = {
            baseSegmentId,
            maxDistance: maxDistance ?? 1,
            adjacentSegments: segments,
            totalAdjacent: segments.length,
          };
          break;
        }

        case 'identify_speaker': {
          const { segmentId, expectedSpeaker, priorityPatterns, excludePatterns } = args as {
            segmentId: number;
            expectedSpeaker?: string;
            priorityPatterns?: string[];
            excludePatterns?: string[];
          };

          // Build options object from dynamic patterns
          const options = (priorityPatterns || excludePatterns)
            ? { priorityPatterns, excludePatterns }
            : undefined;

          if (expectedSpeaker) {
            // Validation mode
            result = validateSpeaker(db, segmentId, expectedSpeaker, logger, options);
          } else {
            // Identification mode
            const segment = db.prepare(`SELECT content FROM segments WHERE id = ?`).get(segmentId) as { content: string } | undefined;
            if (!segment) throw errorHandler.createInvalidParamsError(`Segment ${segmentId} not found`);

            result = identifySpeaker(segment.content, undefined, logger, options);
          }
          break;
        }

        case 'detect_pattern_contamination': {
          const { claimedOutput, segmentId, patterns } = args as {
            claimedOutput: string;
            segmentId: number;
            patterns?: Array<{
              trigger: string;
              expectedCompletion: string;
              description?: string;
            }>;
          };

          const segment = db.prepare(`SELECT content FROM segments WHERE id = ?`).get(segmentId) as { content: string } | undefined;
          if (!segment) throw errorHandler.createInvalidParamsError(`Segment ${segmentId} not found`);

          result = detectPatternContamination(claimedOutput, segment.content, logger, patterns);
          break;
        }

        case 'validate_extraction_schema': {
          const { output, fields, allowCommentary } = args as {
            output: string;
            fields: string[];
            allowCommentary?: boolean;
          };

          const schema = createExtractionSchema(fields, {
            allowCommentary: allowCommentary ?? false,
            requireConfidence: true,
          });

          result = validateExtractionSchema(output, schema, logger);
          break;
        }

        // ====================================================================
        // NEW: NARRATIVE VOICE & AGENCY HANDLERS
        // ====================================================================

        case 'detect_narrative_voice': {
          const { segmentId, domainVocabulary } = args as {
            segmentId: number;
            domainVocabulary?: DomainVocabulary;
          };

          const segment = db.prepare(`SELECT content FROM segments WHERE id = ?`).get(segmentId) as { content: string } | undefined;
          if (!segment) throw errorHandler.createInvalidParamsError(`Segment ${segmentId} not found`);

          result = detectNarrativeVoice(segment.content, domainVocabulary, logger);
          break;
        }

        case 'validate_agency_execution': {
          const { segmentId, agentPatterns, domainVocabulary } = args as {
            segmentId: number;
            agentPatterns?: string[];
            domainVocabulary?: DomainVocabulary;
          };

          const segment = db.prepare(`SELECT content FROM segments WHERE id = ?`).get(segmentId) as { content: string } | undefined;
          if (!segment) throw errorHandler.createInvalidParamsError(`Segment ${segmentId} not found`);

          result = validateAgencyExecution(segment.content, agentPatterns, domainVocabulary, logger);
          break;
        }

        case 'detect_weak_quantifiers': {
          const { text } = args as {
            text: string;
          };

          result = detectWeakQuantifiers(text, logger);
          break;
        }

        // ====================================================================
        // NEW: EXISTENTIAL RESPONSE VALIDATION HANDLERS
        // ====================================================================

        case 'detect_inference_violations': {
          const { text } = args as {
            text: string;
          };

          // Detect evasion patterns which include inference violations
          result = detectEvasionPatterns(text, logger);
          break;
        }

        case 'validate_existential_response': {
          const { response } = args as {
            response: string;
          };

          result = validateExistentialResponse(response, logger);
          break;
        }

        case 'generate_safe_fallback': {
          const { questionType, documentTitle } = args as {
            questionType: 'synthesis' | 'explanation' | 'causality' | 'teleology' | 'cross_section';
            documentTitle: string;
          };

          // Use existing generateSafeFallback from cognitive-constraints or create new one
          result = generateExistentialFallback(false, 0, documentTitle);
          break;
        }

        // ====================================================================
        // NEW: SPEECH VS ACTION CLASSIFICATION HANDLERS
        // ====================================================================

        case 'detect_text_genre': {
          const { segmentId, domainVocabulary } = args as {
            segmentId: number;
            domainVocabulary?: DomainVocabulary;
          };

          const segment = db.prepare(`SELECT content FROM segments WHERE id = ?`).get(segmentId) as { content: string } | undefined;
          if (!segment) throw errorHandler.createInvalidParamsError(`Segment ${segmentId} not found`);

          // Pass domain vocabulary for enhanced detection
          result = detectTextGenre(segment.content, domainVocabulary, logger);
          break;
        }

        case 'detect_divine_agency_without_speech': {
          const { segmentId, agentPatterns, domainVocabulary } = args as {
            segmentId: number;
            agentPatterns?: string[];
            domainVocabulary?: DomainVocabulary;
          };

          const segment = db.prepare(`SELECT content FROM segments WHERE id = ?`).get(segmentId) as { content: string } | undefined;
          if (!segment) throw errorHandler.createInvalidParamsError(`Segment ${segmentId} not found`);

          // Pass agent patterns and domain vocabulary (no hardcoded defaults)
          result = detectDivineAgencyWithoutSpeech(segment.content, agentPatterns, domainVocabulary, logger);
          break;
        }

        default:
          throw errorHandler.createInvalidParamsError(`Unknown tool: ${name}`);
      }

      return {
        content: [
          {
            type: 'text' as const,
            text: JSON.stringify(result, null, 2),
          },
        ],
      };
    } catch (error) {
      logger.error('Tool execution failed', { name, error: String(error) });
      throw error;
    }
  });
}

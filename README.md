# BigContext MCP

MCP Server for handling large documents with intelligent segmentation and TF-IDF search. Designed to work with documents of any size without saturating the model context window.

## Overview

BigContext MCP allows Claude to work with extensive documents (books, manuals, research papers) by loading only relevant fragments per query, instead of the entire document. It uses automatic segmentation and TF-IDF keyword search to retrieve the most relevant content.

## Key Features

### Document Processing
- **Multi-format support**: txt, md, PDF, EPUB, HTML
- **Automatic segmentation**: Detects chapters, sections, and hierarchical structure
- **Efficient storage**: SQLite with WAL mode for concurrent access
- **TF-IDF indexing**: Fast semantic search without external embeddings

### Extraction Validation Tools (Domain-Agnostic)

A comprehensive suite of **27 domain-agnostic tools** for preventing hallucination and ensuring grounded text analysis:

#### 1. **Literal Quote Validation**
- `validate_literal_quote`: Verifies that quoted text exists EXACTLY in the source
- Prevents pattern completion hallucination
- Returns confidence levels: "textual" (exact), "partial" (similar), or "not_found"

#### 2. **Proximity Validation**
- `validate_proximity`: Ensures segments are adjacent (same verse or verse+1)
- `get_adjacent_segments`: Gets segments within proximity constraint
- Prevents narrative jump violations

#### 3. **Speaker Identification**
- `identify_speaker`: Detects who is speaking in a segment
- Domain-agnostic: works with any document type (religious, legal, literary, academic)
- Accepts dynamic `priorityPatterns` and `excludePatterns`

#### 4. **Pattern Contamination Detection**
- `detect_pattern_contamination`: Detects when output completes known patterns not in source
- Agent provides pattern definitions dynamically based on document genre
- Works for any genre: Biblical, fairy tales, legal formulas, academic citations

#### 5. **Extraction Schema Validation**
- `validate_extraction_schema`: Validates pure data extraction without commentary
- Detects parenthetical comments, notes sections, evaluative language
- Enforces strict schema compliance

#### 6. **Narrative Voice Detection** ⭐
- `detect_narrative_voice`: Distinguishes voice types in text
  - **primary_narration**: "The agent did X" = action executed in-scene
  - **human_to_divine**: "You led them" = retrospective prayer/praise
  - **divine_direct_speech**: "I am the X" = agent speaking
  - **human_about_divine**: "The X is my shepherd" = descriptive
- **DOMAIN-AGNOSTIC**: Accepts optional `DomainVocabulary` parameter
- Works with structural patterns alone if no vocabulary provided
- Agent provides agents, verbs, and formulas dynamically

#### 7. **Agency Execution Validation** ⭐
- `validate_agency_execution`: Distinguishes EXECUTED vs REFERENCED actions
  - **EXECUTED**: "Fire came up from the rock" (primary narration)
  - **REFERENCED**: "You led them with a pillar" (retrospective memory)
- **DOMAIN-AGNOSTIC**: Accepts `agentPatterns` and `DomainVocabulary`
- Returns: isExecuted, mode (executed/retrospective/prospective/hypothetical)

#### 8. **Text Genre Detection** ⭐
- `detect_text_genre`: Identifies genre based on structure and patterns
- Genres: historical_narrative, narrative_poetry, prayer_praise, recapitulation, prophetic
- **DOMAIN-AGNOSTIC**: Structural patterns + optional `domainVocabulary`
- Agent provides domain-specific vocabulary dynamically

#### 9. **Divine Agency Without Speech** ⭐
- `detect_divine_agency_without_speech`: Finds actions without speech verbs
- **DOMAIN-AGNOSTIC**: No hardcoded defaults
- Agent provides `agentPatterns` and `domainVocabulary` dynamically
- Separates SPEECH_VERB_WHITELIST from CAUSAL_ACTION_VERBS

#### 10. **Weak Quantifier Detection**
- `detect_weak_quantifiers`: Detects unsupported generalizations
- Flags: "frequently", "typically", "generally", "always", "never"
- Returns recommendation: "allow", "require_count", or "block"

#### 11. **Existential Response Validation**
- `validate_existential_response`: Validates YES/NO question responses
- VALID: "YES" + evidence OR "NO" + explicit denial
- INVALID: meta-discourse, hedging, evasion

#### 12. **Source Capabilities Analysis**
- `get_source_capabilities`: Analyzes what a document CAN and CANNOT support
- Detects languages, original text availability, textual variants
- Returns epistemological limitations

#### 13. **Claim Validation**
- `validate_claim`: Checks if a claim requires capabilities the document lacks
- Prevents assertions about morphology, etymology without source support

#### 14. **Epistemological Reporting**
- `get_epistemological_report`: Complete analysis before scholarly claims
- Returns language hard stops, canonical frame detection, auto-critique
- Confidence decay calculation

#### 15. **Language Operation Checking**
- `check_language_operation`: Validates linguistic operations
- Checks morphological, etymological, text-critical analysis permissions

#### 16. **Semantic Frame Detection**
- `detect_semantic_frames`: Identifies conceptual frameworks
- Frameworks: causal, revelational, performative, invocative
- Prevents reductive analysis

#### 17. **Subdetermination Analysis**
- `analyze_subdetermination`: Distinguishes indeterminacy from subdetermination
- Returns what text CLOSES (excludes) vs LEAVES OPEN

#### 18. **Performative Detection**
- `detect_performatives`: Identifies performative speech acts
- Detects patterns where divine speech IS the creative act

#### 19. **Anachronism Checking**
- `check_anachronisms`: Detects imported post-biblical concepts
- Flags: Aristotelian causes, Neoplatonic emanation, Trinitarian doctrine

#### 20. **Cognitive Operation Auditing**
- `audit_cognitive_operations`: Validates query and output compliance
- Detects unauthorized operations: synthesis, explanation, causality inference
- Returns compliance status and safe fallback

#### 21. **Output Vocabulary Validation**
- `validate_output_vocabulary`: Checks if output uses only source vocabulary
- Detects terms imported from outside the text

#### 22. **Inference Violation Detection**
- `detect_inference_violations`: Scans for unauthorized connectors
- Flags: "therefore", "thus", "implies", "means that"
- Detects prohibited abstract nouns

#### 23. **Permitted Operations**
- `get_permitted_operations`: Returns allowed operations per text type
- Different genres allow different operations

#### 24. **Safe Fallback Generation**
- `generate_safe_fallback`: Generates compliant response when violations detected

#### 25. **Document Vocabulary Building**
- `build_document_vocabulary`: Creates closed vocabulary from document
- Required before using `validate_output_vocabulary`

## Domain-Agnostic Architecture

### DomainVocabulary Interface

All extraction validators accept an optional `DomainVocabulary` parameter:

```typescript
interface DomainVocabulary {
  agents?: string[];              // ['God', 'Lord'] or ['Allah'] or ['the Court']
  addressees?: string[];          // ['Lord', 'God'] or ['Your Honor']
  oracleFormulas?: string[];      // ['thus says the Lord'] or ['the Court finds']
  praiseFormulas?: string[];      // ['praise the Lord'] or ['glory to Allah']
  actionVerbs?: string[];         // ['led', 'brought', 'gave', 'made', 'created']
  narrationVerbs?: string[];      // ['said', 'spoke', 'did', 'made', 'saw']
  stateVerbs?: string[];          // ['is', 'was', 'has been', 'will be']
}
```

### Example Usage

**Biblical text:**
```typescript
{
  agents: ['God', 'Lord', 'Moses'],
  addressees: ['Lord', 'God'],
  actionVerbs: ['led', 'brought', 'gave', 'made', 'created', 'saved', 'delivered'],
  narrationVerbs: ['said', 'spoke', 'did', 'made', 'saw', 'blessed'],
  stateVerbs: ['is', 'was', 'has been'],
  oracleFormulas: ['thus says the Lord'],
  praiseFormulas: ['praise the Lord']
}
```

**Legal documents:**
```typescript
{
  agents: ['the Court', 'Plaintiff', 'Defendant'],
  addressees: ['Your Honor'],
  actionVerbs: ['ruled', 'ordered', 'granted', 'denied'],
  narrationVerbs: ['stated', 'found', 'held', 'declared'],
  stateVerbs: ['is', 'was'],
  oracleFormulas: ['the Court finds'],
  praiseFormulas: []
}
```

**Quranic text:**
```typescript
{
  agents: ['Allah', 'the Prophet'],
  addressees: ['Allah'],
  actionVerbs: ['guided', 'sent', 'revealed', 'blessed'],
  narrationVerbs: ['said', 'commanded', 'decreed'],
  stateVerbs: ['is', 'was'],
  oracleFormulas: ['Allah says'],
  praiseFormulas: ['glory to Allah']
}
```

## Installation

```bash
npm install
npm run build
```

## Configuration

Add to your `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "bigcontext": {
      "command": "node",
      "args": ["/path/to/bigcontext-mcp/dist/index.js"]
    }
  }
}
```

## Usage Examples

### 1. Ingest a document
```typescript
// Ingest a PDF book
const result = await ingest_document({
  path: "/path/to/document.pdf",
  title: "My Document",
  chunkSize: 2000,
  overlap: 100
});
```

### 2. Search for content
```typescript
// Search within document
const results = await search_segment({
  query: "agency without speech",
  documentId: 2,
  limit: 5
});
```

### 3. Validate narrative voice (domain-agnostic)
```typescript
// Biblical context
const voice = await detect_narrative_voice({
  segmentId: 722,
  domainVocabulary: {
    agents: ['God', 'Lord'],
    addressees: ['Lord', 'God'],
    actionVerbs: ['led', 'brought', 'gave', 'made'],
    narrationVerbs: ['said', 'spoke', 'did', 'made']
  }
});

// Legal context
const voice = await detect_narrative_voice({
  segmentId: 123,
  domainVocabulary: {
    agents: ['the Court', 'Plaintiff'],
    addressees: ['Your Honor'],
    actionVerbs: ['ruled', 'ordered', 'granted'],
    narrationVerbs: ['stated', 'found', 'held']
  }
});
```

### 4. Validate agency execution (domain-agnostic)
```typescript
const validation = await validate_agency_execution({
  segmentId: 762,
  agentPatterns: ['God', 'Lord'],
  domainVocabulary: {
    actionVerbs: ['led', 'brought', 'gave'],
    narrationVerbs: ['said', 'spoke', 'did', 'remembered', 'drove']
  }
});
// Returns: { isExecuted: true, mode: 'executed', agent: 'Lord', action: 'drove' }
```

### 5. Detect genre (domain-agnostic)
```typescript
const genre = await detect_text_genre({
  segmentId: 1075,
  domainVocabulary: {
    agents: ['God', 'He'],
    oracleFormulas: ['thus says the Lord'],
    praiseFormulas: ['praise the Lord']
  }
});
// Returns: { genre: 'narrative_poetry', confidence: 'high' }
```

### 6. Detect agency without speech
```typescript
const agency = await detect_divine_agency_without_speech({
  segmentId: 722,
  agentPatterns: ['God', 'Lord'],
  domainVocabulary: {
    agents: ['God', 'Lord'],
    narrationVerbs: ['remembered', 'drove', 'caused', 'made']
  }
});
// Returns: { found: true, agent: 'God', actionVerb: 'remembered', hasSpeechVerb: false }
```

## Architecture Highlights

### Structural Pattern Matching
- **Pure structural patterns** detect grammatical structure without vocabulary
- **Dynamic pattern generation** combines structure + agent-provided vocabulary
- **Fallback mechanisms** work with generic patterns when no vocabulary provided

### No Hardcoded Assumptions
- **Zero biblical terms hardcoded** in validation logic
- **Zero legal terms hardcoded**
- **Zero religious assumptions**
- Agent provides ALL domain-specific vocabulary at runtime

### Separation of Concerns
- **SPEECH_VERB_WHITELIST**: 38 speech verbs (said, spoke, called, etc.)
- **CAUSAL_ACTION_VERBS**: 90+ action verbs (caused, drove, made, etc.)
- **STRUCTURAL_NARRATIVE_VOICE_PATTERNS**: Grammar-only patterns
- **DomainVocabulary**: Agent-provided dynamic vocabulary

## Development

```bash
# Install dependencies
npm install

# Build
npm run build

# Development mode
npm run dev
```

## Technical Stack

- **TypeScript** - Type-safe implementation
- **SQLite (better-sqlite3)** - Fast local storage with WAL mode
- **Zod** - Schema validation
- **pdf-parse** - PDF text extraction
- **@gxl/epub-parser** - EPUB support
- **cheerio** - HTML parsing
- **natural** - NLP tokenization

## License

MIT

## Achievements

### V15: Domain-Agnostic Extraction Validators (2026-01-10)

**Problem Solved:**
- All extraction validators had hardcoded biblical terms ("God", "Lord", "Moses")
- Tools were not reusable for other domains (legal, Quranic, literary, academic)
- Agent could not dynamically provide domain-specific vocabulary

**Solution Implemented:**
1. **Expanded DomainVocabulary interface** with 7 dynamic properties (agents, addressees, actionVerbs, narrationVerbs, stateVerbs, oracleFormulas, praiseFormulas)
2. **Refactored STRUCTURAL_NARRATIVE_VOICE_PATTERNS** to detect only grammatical structure (no vocabulary)
3. **Refactored detectNarrativeVoice()** to accept optional `DomainVocabulary` parameter
4. **Refactored validateAgencyExecution()** to accept `agentPatterns` and `DomainVocabulary`
5. **Updated tool registrations** with domain-agnostic schemas and descriptions
6. **Verified zero hardcoded terms** in all 27 extraction validators

**Impact:**
- ✅ Tools now work with ANY domain (biblical, legal, Quranic, literary, academic)
- ✅ Agent provides ALL vocabulary dynamically at runtime
- ✅ Structural patterns work as fallback when no vocabulary provided
- ✅ Compilation successful with zero hardcoded assumptions

---

### Previous Achievements

**V14: Speech vs Action Verb Separation**
- Created `SPEECH_VERB_WHITELIST` (38 speech verbs)
- Created `CAUSAL_ACTION_VERBS` (90+ action verbs)
- Separated illocutory acts from narrative agency

**V13: Narrative Voice Detection**
- Implemented `detectNarrativeVoice()` to distinguish primary narration from retrospective prayer
- Solved FALSE NEGATIVE problem: verses where God acts without speaking

**V12: Extraction Schema Validators**
- 25 comprehensive tools for preventing hallucination
- Literal quote validation, proximity checking, pattern contamination detection

**V1-V11: Core Infrastructure**
- Multi-format document ingestion (txt, md, PDF, EPUB, HTML)
- Automatic segmentation by chapters and sections
- TF-IDF search implementation
- SQLite storage with WAL mode

---

## Future Roadmap

### Planned Migration to Python + uvx

We are planning to migrate BigContext MCP to Python with `uvx` distribution for significantly improved developer experience.

#### Why Python + uvx?

**Current limitation (TypeScript/Node.js):**
```bash
# Users must clone repository locally
git clone https://github.com/Rixmerz/bigcontext_mcp.git
cd bigcontext_mcp
npm install
npm run build

# Then configure in Claude Desktop
{
  "mcpServers": {
    "bigcontext": {
      "command": "node",
      "args": ["/absolute/path/to/bigcontext-mcp/dist/index.js"]
    }
  }
}
```

**Planned improvement (Python + uvx):**
```bash
# NO need to clone repository!
# Direct installation via uvx
uvx bigcontext-mcp

# Auto-configured in Claude Desktop
{
  "mcpServers": {
    "bigcontext": {
      "command": "uvx",
      "args": ["bigcontext-mcp"]
    }
  }
}
```

#### Benefits of uvx Distribution

1. **Zero local cloning** - Install directly from PyPI
2. **Automatic dependency management** - uvx handles Python environment
3. **Cross-platform** - Works on macOS, Linux, Windows
4. **Version management** - Easy updates via `uvx bigcontext-mcp@latest`
5. **Simplified configuration** - No absolute paths needed

#### Migration Plan

- [ ] Port TypeScript codebase to Python
- [ ] Maintain API compatibility (same 27 tools)
- [ ] Package for PyPI distribution
- [ ] Test uvx installation workflow
- [ ] Update documentation
- [ ] Deprecate Node.js version after Python stability

#### Technical Stack (Python)

- **FastMCP** - MCP server framework
- **SQLite** - Same database (compatible)
- **PyPDF2** - PDF parsing
- **beautifulsoup4** - HTML parsing
- **ebooklib** - EPUB support
- **scikit-learn** - TF-IDF (or custom implementation)

#### Timeline

Target: Q2 2026

**Contributions welcome!** If you're interested in helping with the Python migration, please open an issue or PR.

---

## Contributing

We welcome contributions! Areas of interest:
- Python migration to uvx
- Additional domain vocabularies (legal, academic, literary)
- New extraction validators
- Performance optimizations
- Documentation improvements

## Support

- **Issues**: https://github.com/Rixmerz/bigcontext_mcp/issues
- **Discussions**: https://github.com/Rixmerz/bigcontext_mcp/discussions

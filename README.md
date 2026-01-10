# BigContext MCP

MCP Server for handling large documents with intelligent segmentation and TF-IDF search. Designed to work with documents of any size without saturating the model context window.

## Installation

### Via uvx (Recommended)

No need to clone the repository! Install directly:

```bash
uvx --from git+https://github.com/Rixmerz/bigcontext_mcp.git bigcontext-mcp
```

### Configuration for Claude Desktop

Add to your `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "bigcontext": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/Rixmerz/bigcontext_mcp.git",
        "bigcontext-mcp"
      ]
    }
  }
}
```

Restart Claude Desktop and the 31 BigContext tools will be available.

## Overview

BigContext MCP allows Claude to work with extensive documents (books, manuals, research papers) by loading only relevant fragments per query, instead of the entire document. It uses automatic segmentation and TF-IDF keyword search to retrieve the most relevant content.

## Key Features

### Document Processing
- **Multi-format support**: txt, md, PDF, EPUB, HTML
- **Automatic segmentation**: Detects chapters, sections, and hierarchical structure
- **Efficient storage**: SQLite with WAL mode for concurrent access
- **TF-IDF indexing**: Fast semantic search without external embeddings

### 31 Domain-Agnostic Tools

#### Core Tools (5)
| Tool | Description |
|------|-------------|
| `ingest_document` | Load, segment, and index a document |
| `search_segment` | Search for relevant segments using TF-IDF |
| `get_metadata` | Get metadata, structure, and top terms |
| `list_documents` | List all indexed documents |
| `compare_segments` | Compare two segments for themes and similarity |

#### Epistemology Tools (4)
| Tool | Description |
|------|-------------|
| `get_source_capabilities` | Analyze what a document CAN and CANNOT support |
| `validate_claim` | Check if a claim can be grounded in the source |
| `get_epistemological_report` | Complete analysis before scholarly claims |
| `check_language_operation` | Validate linguistic operations |

#### Semantic Tools (4)
| Tool | Description |
|------|-------------|
| `detect_semantic_frames` | Identify conceptual frameworks (causal, revelational, performative) |
| `analyze_subdetermination` | Distinguish indeterminacy from subdetermination |
| `detect_performatives` | Identify performative speech acts |
| `check_anachronisms` | Detect imported post-biblical concepts |

#### Cognitive Tools (4)
| Tool | Description |
|------|-------------|
| `audit_cognitive_operations` | Validate query and output compliance |
| `detect_inference_violations` | Scan for unauthorized connectors |
| `get_permitted_operations` | Get allowed operations per text type |
| `generate_safe_fallback` | Generate compliant response when violations detected |

#### Extraction Validators (14)
| Tool | Description |
|------|-------------|
| `validate_literal_quote` | Verify quoted text exists EXACTLY in source |
| `validate_proximity` | Check if segments are adjacent |
| `get_adjacent_segments` | Get segments within proximity constraint |
| `identify_speaker` | Detect who is speaking in a segment |
| `detect_pattern_contamination` | Detect pattern completion not in source |
| `validate_extraction_schema` | Validate pure data extraction |
| `detect_narrative_voice` | Distinguish voice types in text |
| `validate_agency_execution` | Distinguish EXECUTED vs REFERENCED actions |
| `detect_text_genre` | Identify genre based on structure |
| `detect_divine_agency_without_speech` | Find actions without speech verbs |
| `detect_weak_quantifiers` | Detect unsupported generalizations |
| `validate_existential_response` | Validate YES/NO question responses |
| `build_document_vocabulary` | Create closed vocabulary from document |
| `validate_output_vocabulary` | Check if output uses only source vocabulary |

## Domain-Agnostic Architecture

All extraction validators accept an optional `DomainVocabulary` parameter:

```python
class DomainVocabulary(BaseModel):
    agents: list[str] | None = None        # ['God', 'Lord'] or ['the Court']
    addressees: list[str] | None = None    # ['Lord'] or ['Your Honor']
    oracle_formulas: list[str] | None = None    # ['thus says the Lord']
    praise_formulas: list[str] | None = None    # ['praise the Lord']
    action_verbs: list[str] | None = None       # ['led', 'brought', 'created']
    narration_verbs: list[str] | None = None    # ['said', 'spoke', 'did']
    state_verbs: list[str] | None = None        # ['is', 'was', 'has been']
```

### Example: Biblical Text
```json
{
  "agents": ["God", "Lord", "Moses"],
  "addressees": ["Lord", "God"],
  "action_verbs": ["led", "brought", "gave", "made", "created"],
  "narration_verbs": ["said", "spoke", "did", "made", "saw"],
  "oracle_formulas": ["thus says the Lord"],
  "praise_formulas": ["praise the Lord"]
}
```

### Example: Legal Documents
```json
{
  "agents": ["the Court", "Plaintiff", "Defendant"],
  "addressees": ["Your Honor"],
  "action_verbs": ["ruled", "ordered", "granted", "denied"],
  "narration_verbs": ["stated", "found", "held", "declared"],
  "oracle_formulas": ["the Court finds"],
  "praise_formulas": []
}
```

## Usage Examples

### 1. Ingest a document
```python
result = ingest_document(
    path="/path/to/document.pdf",
    title="My Document",
    chunk_size=2000,
    overlap=100
)
# Returns: document_id, total_segments, structure
```

### 2. Search for content
```python
results = search_segment(
    query="agency without speech",
    document_id=1,
    limit=5
)
# Returns: matched segments with scores and snippets
```

### 3. Validate narrative voice
```python
voice = detect_narrative_voice(
    segment_id=722,
    domain_vocabulary={
        "agents": ["God", "Lord"],
        "addressees": ["Lord", "God"],
        "action_verbs": ["led", "brought", "gave", "made"]
    }
)
# Returns: voice_type, confidence, evidence, is_retrospective
```

### 4. Validate agency execution
```python
validation = validate_agency_execution(
    segment_id=762,
    divine_agent_patterns=["God", "Lord"]
)
# Returns: is_executed, mode, agent, action, evidence
```

### 5. Detect text genre
```python
genre = detect_text_genre(
    segment_id=1075,
    domain_vocabulary={
        "agents": ["God", "He"],
        "oracle_formulas": ["thus says the Lord"],
        "praise_formulas": ["praise the Lord"]
    }
)
# Returns: genre, confidence, indicators
```

## Technical Stack

- **Python 3.11+** - Modern Python with type hints
- **FastMCP 2.x** - MCP server framework with decorator-based tools
- **Pydantic 2.x** - Schema validation
- **SQLite** - Local storage with WAL mode
- **pdfplumber** - PDF text extraction
- **ebooklib** - EPUB support
- **beautifulsoup4** - HTML parsing
- **NLTK** - NLP tokenization

## Development

### Local Installation

```bash
# Clone repository
git clone https://github.com/Rixmerz/bigcontext_mcp.git
cd bigcontext_mcp

# Create virtual environment
uv venv .venv
source .venv/bin/activate

# Install in development mode
uv pip install -e .

# Run server
python -m bigcontext_mcp
```

### Local Testing with Claude Desktop

```json
{
  "mcpServers": {
    "bigcontext": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/bigcontext-mcp",
        "bigcontext-mcp"
      ]
    }
  }
}
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

## Changelog

### V16: Python Migration (2026-01-10)

**Complete rewrite from TypeScript to Python:**
- Framework: FastMCP 2.x with decorator-based tool registration
- Distribution: uvx-ready (zero-clone install from GitHub)
- Database: SQLite with WAL mode (same schema, compatible)
- Validation: Pydantic replacing Zod
- Total: 31 MCP tools migrated and tested

### V15: Domain-Agnostic Extraction Validators

- Expanded DomainVocabulary interface with 7 dynamic properties
- Refactored all validators to accept optional vocabulary parameter
- Zero hardcoded domain-specific terms

### V14: Speech vs Action Verb Separation

- Created SPEECH_VERB_WHITELIST (38 speech verbs)
- Created CAUSAL_ACTION_VERBS (90+ action verbs)

### V1-V13: Core Infrastructure

- Multi-format document ingestion (txt, md, PDF, EPUB, HTML)
- Automatic segmentation by chapters and sections
- TF-IDF search implementation
- SQLite storage with WAL mode
- 27 extraction validation tools

## License

MIT

## Contributing

We welcome contributions! Areas of interest:
- Additional domain vocabularies (legal, academic, literary)
- New extraction validators
- Performance optimizations
- Documentation improvements

## Support

- **Issues**: https://github.com/Rixmerz/bigcontext_mcp/issues
- **Repository**: https://github.com/Rixmerz/bigcontext_mcp

"""Pydantic models for BigContext MCP."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# Enums
class DocumentFormat(str, Enum):
    """Supported document formats."""

    TXT = "txt"
    MD = "md"
    PDF = "pdf"
    EPUB = "epub"
    HTML = "html"


class SegmentType(str, Enum):
    """Types of document segments."""

    CHAPTER = "chapter"
    SECTION = "section"
    PARAGRAPH = "paragraph"
    CHUNK = "chunk"


class NarrativeVoiceType(str, Enum):
    """Types of narrative voice in text."""

    PRIMARY_NARRATION = "primary_narration"
    HUMAN_TO_DIVINE = "human_to_divine"
    DIVINE_DIRECT_SPEECH = "divine_direct_speech"
    HUMAN_ABOUT_DIVINE = "human_about_divine"
    UNKNOWN = "unknown"


class TextGenre(str, Enum):
    """Types of text genre."""

    HISTORICAL_NARRATIVE = "historical_narrative"
    NARRATIVE_POETRY = "narrative_poetry"
    PRAYER_PRAISE = "prayer_praise"
    RECAPITULATION = "recapitulation"
    PROPHETIC = "prophetic"
    UNKNOWN = "unknown"


class AgencyMode(str, Enum):
    """Mode of agency execution."""

    EXECUTED = "executed"
    RETROSPECTIVE = "retrospective"
    PROSPECTIVE = "prospective"
    HYPOTHETICAL = "hypothetical"
    UNKNOWN = "unknown"


# Domain-agnostic vocabulary for extraction validators
class DomainVocabulary(BaseModel):
    """
    Domain-specific vocabulary for extraction validators.
    Agent provides ALL vocabulary dynamically at runtime.
    """

    agents: list[str] | None = Field(
        default=None,
        description="Primary agents/actors (e.g., ['God', 'Lord'] or ['the Court'])",
    )
    addressees: list[str] | None = Field(
        default=None,
        description="Terms for addressing authority (e.g., ['Lord'] or ['Your Honor'])",
    )
    oracle_formulas: list[str] | None = Field(
        default=None,
        description="Proclamation formulas (e.g., ['thus says the Lord'])",
    )
    praise_formulas: list[str] | None = Field(
        default=None,
        description="Praise/worship terms (e.g., ['praise the Lord'])",
    )
    action_verbs: list[str] | None = Field(
        default=None,
        description="Action verbs in retrospective contexts (e.g., ['led', 'brought'])",
    )
    narration_verbs: list[str] | None = Field(
        default=None,
        description="Narration verbs in primary narration (e.g., ['said', 'spoke'])",
    )
    state_verbs: list[str] | None = Field(
        default=None,
        description="State/identity verbs (e.g., ['is', 'was'])",
    )


# Database models
class Document(BaseModel):
    """Document stored in database."""

    id: int
    path: str
    title: str
    format: DocumentFormat
    total_words: int = 0
    total_segments: int = 0
    file_hash: str
    created_at: datetime


class Segment(BaseModel):
    """Segment of a document."""

    id: int
    document_id: int
    parent_segment_id: int | None = None
    type: SegmentType
    title: str | None = None
    content: str
    word_count: int
    position: int


class TermFrequency(BaseModel):
    """Term frequency for a segment."""

    segment_id: int
    term: str
    count: int
    tf: float


class DocumentFrequency(BaseModel):
    """Document frequency for a term."""

    term: str
    df: int
    idf: float


# Result models
class SegmentInfo(BaseModel):
    """Summary info for a segment."""

    segment_id: int
    type: SegmentType
    title: str | None = None
    word_count: int
    position: int


class IngestResult(BaseModel):
    """Result of ingesting a document."""

    success: bool
    document_id: int
    title: str
    format: DocumentFormat
    total_segments: int
    total_words: int
    structure: list[SegmentInfo]
    processing_time_ms: float


class SearchResultItem(BaseModel):
    """Single search result."""

    segment_id: int
    document_id: int
    document_title: str
    segment_title: str | None = None
    segment_type: SegmentType
    score: float
    snippet: str
    matched_terms: list[str]
    position: int


class SearchResult(BaseModel):
    """Search results collection."""

    results: list[SearchResultItem]
    total_matches: int
    query_terms: list[str]


class TermScore(BaseModel):
    """Term with score."""

    term: str
    score: float


class StructureItem(BaseModel):
    """Document structure item."""

    segment_id: int
    type: SegmentType
    title: str | None = None
    word_count: int
    depth: int


class DocumentInfo(BaseModel):
    """Document information."""

    id: int
    path: str
    title: str
    format: DocumentFormat
    total_words: int
    total_segments: int
    created_at: datetime


class SegmentMetadata(BaseModel):
    """Segment metadata."""

    id: int
    type: SegmentType
    title: str | None = None
    word_count: int
    position: int


class MetadataResult(BaseModel):
    """Metadata query result."""

    document: DocumentInfo | None = None
    segment: SegmentMetadata | None = None
    structure: list[StructureItem] | None = None
    top_terms: list[TermScore] | None = None


class SharedTerm(BaseModel):
    """Shared term between segments."""

    term: str
    score_a: float
    score_b: float


class SegmentSummary(BaseModel):
    """Summary of a segment."""

    id: int
    title: str | None = None
    word_count: int


class BridgeSegment(BaseModel):
    """Bridge segment between two segments."""

    segment_id: int
    title: str | None = None
    connection_score: float


class CompareResult(BaseModel):
    """Result of comparing two segments."""

    segment_a: SegmentSummary
    segment_b: SegmentSummary
    similarity_score: float
    shared_themes: list[SharedTerm]
    unique_to_a: list[TermScore]
    unique_to_b: list[TermScore]
    bridge_segments: list[BridgeSegment] | None = None


class ParsedDocument(BaseModel):
    """Result of parsing a document."""

    content: str
    metadata: dict[str, Any] | None = None


class DetectedSegment(BaseModel):
    """Detected segment in document."""

    type: SegmentType
    title: str | None = None
    content: str
    start_offset: int
    end_offset: int


# Extraction validator result models
class NarrativeVoiceResult(BaseModel):
    """Result of narrative voice detection."""

    voice_type: NarrativeVoiceType
    confidence: str  # "high", "medium", "low"
    evidence: list[str]
    is_retrospective: bool = False


class AgencyExecutionResult(BaseModel):
    """Result of agency execution validation."""

    is_executed: bool
    mode: AgencyMode
    agent: str | None = None
    action: str | None = None
    evidence: list[str]
    warning: str | None = None


class TextGenreResult(BaseModel):
    """Result of text genre detection."""

    genre: TextGenre
    confidence: str  # "high", "medium", "low"
    indicators: list[str]


class SpeakerIdentificationResult(BaseModel):
    """Result of speaker identification."""

    speaker: str | None = None
    confidence: str  # "explicit", "contextual", "ambiguous", "unknown"
    evidence: list[str]
    is_expected_speaker: bool | None = None


class LiteralQuoteResult(BaseModel):
    """Result of literal quote validation."""

    confidence: str  # "textual", "partial", "not_found"
    matched_text: str | None = None
    similarity: float | None = None


class PatternContaminationResult(BaseModel):
    """Result of pattern contamination detection."""

    is_contaminated: bool
    pattern_name: str | None = None
    expected_completion: str | None = None
    actual_text: str | None = None


class ExtractionSchemaResult(BaseModel):
    """Result of extraction schema validation."""

    is_valid: bool
    violations: list[str]
    has_commentary: bool
    has_evaluative_language: bool


class WeakQuantifierResult(BaseModel):
    """Result of weak quantifier detection."""

    quantifiers_found: list[str]
    recommendation: str  # "allow", "require_count", "block"


class ExistentialResponseResult(BaseModel):
    """Result of existential response validation."""

    is_valid: bool
    has_answer: bool
    has_evidence: bool
    violations: list[str]


class SourceCapabilitiesResult(BaseModel):
    """Result of source capabilities analysis."""

    document_id: int
    detected_languages: list[str]
    has_original_languages: bool
    has_textual_variants: bool
    has_critical_apparatus: bool
    limitations: list[str]
    supported_claims: list[str]
    unsupported_claims: list[str]


class ClaimValidationResult(BaseModel):
    """Result of claim validation."""

    is_valid: bool
    claim: str
    requires_capability: str | None = None
    document_has_capability: bool
    reason: str | None = None


class EpistemologicalReportResult(BaseModel):
    """Result of epistemological report generation."""

    document_id: int
    query: str
    language_hard_stops: list[str]
    canonical_frame: str | None = None
    auto_critique: list[str]
    confidence_decay: float
    recommendations: list[str]
    capabilities: SourceCapabilitiesResult


class LanguageOperationResult(BaseModel):
    """Result of language operation check."""

    is_allowed: bool
    operation: str
    language: str
    reason: str | None = None
    alternative: str | None = None


class SemanticFrameResult(BaseModel):
    """Result of semantic frame detection."""

    frames: list[str]
    dominant_frame: str | None = None
    frame_evidence: dict[str, list[str]]
    warnings: list[str]


class SubdeterminationResult(BaseModel):
    """Result of subdetermination analysis."""

    closed: list[str]
    left_open: list[str]
    asymmetric_relations: list[str]
    is_indeterminate: bool
    is_subdetermined: bool


class PerformativeResult(BaseModel):
    """Result of performative detection."""

    performatives: list[dict]
    has_performatives: bool
    resists_causal_analysis: bool


class AnachronismResult(BaseModel):
    """Result of anachronism check."""

    anachronisms: list[dict]
    has_anachronisms: bool
    recommendation: str | None = None


class CognitiveAuditResult(BaseModel):
    """Result of cognitive operation audit."""

    is_compliant: bool
    violations: list[dict]
    safe_fallback: str | None = None


class InferenceViolationResult(BaseModel):
    """Result of inference violation detection."""

    has_violations: bool
    connectors_found: list[str]
    abstract_nouns_found: list[str]


class PermittedOperationsResult(BaseModel):
    """Result of permitted operations check."""

    genre: str
    permitted_operations: list[str]
    prohibited_operations: list[str]


class SafeFallbackResult(BaseModel):
    """Result of safe fallback generation."""

    question_type: str
    safe_response: str
    suggestion: str


class VocabularyBuildResult(BaseModel):
    """Result of vocabulary building."""

    document_id: int
    vocabulary_size: int
    vocabulary: list[str]
    top_terms: list[dict]


class VocabularyValidationResult(BaseModel):
    """Result of vocabulary validation."""

    is_valid: bool
    imported_terms: list[str]
    contamination_percentage: float
    total_output_terms: int
    document_vocabulary_size: int


class ProximityResult(BaseModel):
    """Result of proximity validation."""

    is_adjacent: bool
    distance: int
    max_allowed: int

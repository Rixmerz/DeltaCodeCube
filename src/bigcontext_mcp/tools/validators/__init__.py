"""Extraction validators for preventing hallucination and ensuring grounded text analysis."""

from bigcontext_mcp.tools.validators.constants import (
    CAUSAL_ACTION_VERBS,
    SPEECH_VERB_WHITELIST,
    STRUCTURAL_NARRATIVE_VOICE_PATTERNS,
    TEXT_GENRE_INDICATORS,
    WEAK_QUANTIFIERS,
)
from bigcontext_mcp.tools.validators.narrative import (
    detect_narrative_voice,
    validate_agency_execution,
)
from bigcontext_mcp.tools.validators.genre import (
    detect_text_genre,
    detect_divine_agency_without_speech,
)
from bigcontext_mcp.tools.validators.literal import (
    validate_literal_quote,
)
from bigcontext_mcp.tools.validators.proximity import (
    validate_proximity,
    get_adjacent_segment_ids,
)
from bigcontext_mcp.tools.validators.speaker import (
    identify_speaker,
)
from bigcontext_mcp.tools.validators.quantifiers import (
    detect_weak_quantifiers,
)
from bigcontext_mcp.tools.validators.existential import (
    validate_existential_response,
)
from bigcontext_mcp.tools.validators.schema import (
    validate_extraction_schema,
)
from bigcontext_mcp.tools.validators.patterns import (
    detect_pattern_contamination,
)
from bigcontext_mcp.tools.validators.epistemology import (
    get_source_capabilities,
    validate_claim,
    get_epistemological_report,
    check_language_operation,
)
from bigcontext_mcp.tools.validators.semantic import (
    detect_semantic_frames,
    analyze_subdetermination,
    detect_performatives,
    check_anachronisms,
)
from bigcontext_mcp.tools.validators.cognitive import (
    audit_cognitive_operations,
    detect_inference_violations,
    get_permitted_operations,
    generate_safe_fallback,
)
from bigcontext_mcp.tools.validators.vocabulary import (
    build_document_vocabulary,
    validate_output_vocabulary,
)

__all__ = [
    # Constants
    "SPEECH_VERB_WHITELIST",
    "CAUSAL_ACTION_VERBS",
    "STRUCTURAL_NARRATIVE_VOICE_PATTERNS",
    "TEXT_GENRE_INDICATORS",
    "WEAK_QUANTIFIERS",
    # Narrative validators
    "detect_narrative_voice",
    "validate_agency_execution",
    # Genre validators
    "detect_text_genre",
    "detect_divine_agency_without_speech",
    # Literal validators
    "validate_literal_quote",
    # Proximity validators
    "validate_proximity",
    "get_adjacent_segment_ids",
    # Speaker validators
    "identify_speaker",
    # Quantifier validators
    "detect_weak_quantifiers",
    # Existential validators
    "validate_existential_response",
    # Schema validators
    "validate_extraction_schema",
    # Pattern validators
    "detect_pattern_contamination",
    # Epistemology validators
    "get_source_capabilities",
    "validate_claim",
    "get_epistemological_report",
    "check_language_operation",
    # Semantic validators
    "detect_semantic_frames",
    "analyze_subdetermination",
    "detect_performatives",
    "check_anachronisms",
    # Cognitive validators
    "audit_cognitive_operations",
    "detect_inference_violations",
    "get_permitted_operations",
    "generate_safe_fallback",
    # Vocabulary validators
    "build_document_vocabulary",
    "validate_output_vocabulary",
]

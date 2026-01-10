"""FastMCP server for BigContext MCP."""

from typing import Any

from fastmcp import FastMCP

from bigcontext_mcp.db.database import get_connection
from bigcontext_mcp.types import DomainVocabulary

# Import core tools
from bigcontext_mcp.tools.ingest import ingest_document as _ingest_document
from bigcontext_mcp.tools.search import search_segments as _search_segments
from bigcontext_mcp.tools.metadata import (
    get_metadata as _get_metadata,
    get_documents_list as _list_documents,
)
from bigcontext_mcp.tools.compare import compare_segments as _compare_segments

# Import validators
from bigcontext_mcp.tools.validators import (
    # Literal
    validate_literal_quote as _validate_literal_quote,
    # Proximity
    validate_proximity as _validate_proximity,
    get_adjacent_segment_ids as _get_adjacent_segment_ids,
    # Speaker
    identify_speaker as _identify_speaker,
    # Pattern
    detect_pattern_contamination as _detect_pattern_contamination,
    # Schema
    validate_extraction_schema as _validate_extraction_schema,
    # Narrative
    detect_narrative_voice as _detect_narrative_voice,
    validate_agency_execution as _validate_agency_execution,
    # Genre
    detect_text_genre as _detect_text_genre,
    detect_divine_agency_without_speech as _detect_divine_agency_without_speech,
    # Quantifiers
    detect_weak_quantifiers as _detect_weak_quantifiers,
    # Existential
    validate_existential_response as _validate_existential_response,
    # Epistemology
    get_source_capabilities as _get_source_capabilities,
    validate_claim as _validate_claim,
    get_epistemological_report as _get_epistemological_report,
    check_language_operation as _check_language_operation,
    # Semantic
    detect_semantic_frames as _detect_semantic_frames,
    analyze_subdetermination as _analyze_subdetermination,
    detect_performatives as _detect_performatives,
    check_anachronisms as _check_anachronisms,
    # Cognitive
    audit_cognitive_operations as _audit_cognitive_operations,
    detect_inference_violations as _detect_inference_violations,
    get_permitted_operations as _get_permitted_operations,
    generate_safe_fallback as _generate_safe_fallback,
    # Vocabulary
    build_document_vocabulary as _build_document_vocabulary,
    validate_output_vocabulary as _validate_output_vocabulary,
)

from bigcontext_mcp.db.queries import get_segment_by_id

# Import DeltaCodeCube
from bigcontext_mcp.cube import DeltaCodeCube

# Create FastMCP server
mcp = FastMCP("bigcontext")


# =============================================================================
# Core Tools
# =============================================================================


@mcp.tool()
def ingest_document(
    path: str,
    title: str | None = None,
    chunk_size: int = 2000,
    overlap: int = 100,
    force: bool = False,
) -> dict[str, Any]:
    """
    Load, segment, and index a document for search.

    Supports txt, md, pdf, epub, and html formats.
    Automatically detects chapters and sections.

    Args:
        path: Absolute path to the document file.
        title: Optional title for the document (defaults to filename).
        chunk_size: Target size in words for each chunk (default: 2000).
        overlap: Number of words to overlap between chunks (default: 100).
        force: Force re-indexing even if document already exists.

    Returns:
        Ingestion result with document ID and structure.
    """
    with get_connection() as conn:
        result = _ingest_document(
            conn=conn,
            path=path,
            title=title,
            chunk_size=chunk_size,
            overlap=overlap,
            force=force,
        )
        return result.model_dump()


@mcp.tool()
def search_segment(
    query: str,
    document_id: int | None = None,
    segment_id: int | None = None,
    limit: int = 5,
    context_words: int = 50,
) -> dict[str, Any]:
    """
    Search for relevant segments using TF-IDF.

    Returns snippets with matched terms highlighted.

    Args:
        query: Search query (keywords or phrases).
        document_id: Optional: limit search to a specific document.
        segment_id: Optional: search within a specific segment only.
        limit: Maximum number of results to return (default: 5).
        context_words: Number of words around matches in snippets (default: 50).

    Returns:
        Search results with scores and snippets.
    """
    with get_connection() as conn:
        result = _search_segments(
            conn=conn,
            query=query,
            document_id=document_id,
            segment_id=segment_id,
            limit=limit,
            context_words=context_words,
        )
        return result.model_dump()


@mcp.tool()
def get_metadata(
    document_id: int | None = None,
    segment_id: int | None = None,
    include_structure: bool = True,
    top_terms: int = 10,
) -> dict[str, Any]:
    """
    Get metadata, structure, and statistics for a document or segment.

    Includes top terms by TF-IDF.

    Args:
        document_id: ID of the document to get metadata for.
        segment_id: ID of the segment to get metadata for.
        include_structure: Include document structure in response.
        top_terms: Number of top terms to return (default: 10).

    Returns:
        Metadata including structure and top terms.
    """
    with get_connection() as conn:
        result = _get_metadata(
            conn=conn,
            document_id=document_id,
            segment_id=segment_id,
            top_terms=top_terms,
            include_structure=include_structure,
        )
        return result.model_dump()


@mcp.tool()
def list_documents(
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """
    List all indexed documents with their metadata.

    Args:
        limit: Maximum number of documents to return (default: 20).
        offset: Number of documents to skip (for pagination).

    Returns:
        List of documents with metadata.
    """
    with get_connection() as conn:
        result = _list_documents(conn=conn, limit=limit, offset=offset)
        return {"documents": result.documents, "total": result.total}


@mcp.tool()
def compare_segments(
    segment_id_a: int,
    segment_id_b: int,
    find_bridges: bool = True,
    max_bridges: int = 3,
) -> dict[str, Any]:
    """
    Compare two segments to find shared themes, unique terms, and similarity.

    Useful for understanding relationships between chapters.

    Args:
        segment_id_a: ID of the first segment to compare.
        segment_id_b: ID of the second segment to compare.
        find_bridges: Find intermediate segments that connect the two.
        max_bridges: Maximum number of bridge segments to return.

    Returns:
        Comparison result with similarity and themes.
    """
    with get_connection() as conn:
        result = _compare_segments(
            conn=conn,
            segment_id_a=segment_id_a,
            segment_id_b=segment_id_b,
            find_bridges=find_bridges,
            max_bridges=max_bridges,
        )
        return result.model_dump()


# =============================================================================
# Epistemology Tools
# =============================================================================


@mcp.tool()
def get_source_capabilities(document_id: int) -> dict[str, Any]:
    """
    CRITICAL: Analyze what a document CAN and CANNOT support.

    Returns detected languages, whether original Hebrew/Greek/Aramaic is present,
    textual variant availability, and epistemological limitations.
    MUST be called before making claims about morphology, etymology, or textual criticism.

    Args:
        document_id: ID of the document to analyze.

    Returns:
        Source capabilities analysis.
    """
    with get_connection() as conn:
        result = _get_source_capabilities(document_id=document_id, conn=conn)
        return result.model_dump()


@mcp.tool()
def validate_claim(document_id: int, claim: str) -> dict[str, Any]:
    """
    Check if a specific claim can be grounded in the source document.

    Returns whether the claim requires capabilities the document lacks.
    Use this BEFORE making scholarly assertions.

    Args:
        document_id: ID of the document to validate against.
        claim: The claim or assertion to validate.

    Returns:
        Claim validation result.
    """
    with get_connection() as conn:
        result = _validate_claim(document_id=document_id, claim=claim, conn=conn)
        return result.model_dump()


@mcp.tool()
def get_epistemological_report(document_id: int, query: str) -> dict[str, Any]:
    """
    Generate complete epistemological analysis before making scholarly claims.

    Returns: language hard stops, canonical frame detection, auto-critique,
    confidence decay calculation, and recommendations.
    Use BEFORE any complex textual analysis.

    Args:
        document_id: ID of the document to analyze.
        query: The research question or claim being investigated.

    Returns:
        Epistemological report.
    """
    with get_connection() as conn:
        result = _get_epistemological_report(
            document_id=document_id, query=query, conn=conn
        )
        return result.model_dump()


@mcp.tool()
def check_language_operation(
    document_id: int,
    operation: str,
    language: str,
) -> dict[str, Any]:
    """
    Check if a specific linguistic operation is allowed.

    Use before performing morphological, etymological, or text-critical analysis.

    Args:
        document_id: ID of the document.
        operation: The operation to check (e.g., "root analysis").
        language: The language involved (hebrew, greek, aramaic).

    Returns:
        Language operation permission result.
    """
    with get_connection() as conn:
        result = _check_language_operation(
            document_id=document_id, operation=operation, language=language, conn=conn
        )
        return result.model_dump()


# =============================================================================
# Semantic Frame Tools
# =============================================================================


@mcp.tool()
def detect_semantic_frames(segment_id: int, query: str) -> dict[str, Any]:
    """
    Detect conceptual frameworks in a text segment.

    Identifies causal, revelational, performative, and invocative frames.
    Prevents reductive analysis by identifying non-causal categories.

    Args:
        segment_id: ID of the segment to analyze.
        query: The research question being investigated.

    Returns:
        Semantic frame detection result.
    """
    with get_connection() as conn:
        segment = get_segment_by_id(conn, segment_id)
        if not segment:
            return {"error": f"Segment {segment_id} not found"}
        result = _detect_semantic_frames(content=segment["content"], query=query)
        return result.model_dump()


@mcp.tool()
def analyze_subdetermination(segment_id: int) -> dict[str, Any]:
    """
    Analyze whether textual ambiguity is total indeterminacy or directed subdetermination.

    Returns what the text CLOSES (excludes) vs. what it LEAVES OPEN,
    and detects asymmetric relations.

    Args:
        segment_id: ID of the segment to analyze.

    Returns:
        Subdetermination analysis result.
    """
    with get_connection() as conn:
        segment = get_segment_by_id(conn, segment_id)
        if not segment:
            return {"error": f"Segment {segment_id} not found"}
        result = _analyze_subdetermination(content=segment["content"])
        return result.model_dump()


@mcp.tool()
def detect_performatives(segment_id: int) -> dict[str, Any]:
    """
    Detect performative speech acts where divine speech IS the creative act.

    Identifies "And God said... and it was so" patterns that resist causal analysis.

    Args:
        segment_id: ID of the segment to analyze.

    Returns:
        Performative detection result.
    """
    with get_connection() as conn:
        segment = get_segment_by_id(conn, segment_id)
        if not segment:
            return {"error": f"Segment {segment_id} not found"}
        result = _detect_performatives(content=segment["content"])
        return result.model_dump()


@mcp.tool()
def check_anachronisms(query: str) -> dict[str, Any]:
    """
    Check if a research question imports post-biblical conceptual categories.

    Detects Aristotelian causes, Neoplatonic emanation, Trinitarian doctrine.

    Args:
        query: The research question or claim to check.

    Returns:
        Anachronism check result.
    """
    result = _check_anachronisms(query=query)
    return result.model_dump()


# =============================================================================
# Cognitive Operation Tools
# =============================================================================


@mcp.tool()
def audit_cognitive_operations(
    document_id: int,
    query: str,
    planned_output: str,
) -> dict[str, Any]:
    """
    CRITICAL: Run before ANY response. Validates cognitive constraint compliance.

    Detects unauthorized operations (synthesis, explanation, causality inference).
    Returns compliance status and safe fallback if needed.

    Args:
        document_id: ID of the document being queried.
        query: The user query to analyze.
        planned_output: The planned response text to validate.

    Returns:
        Cognitive audit result.
    """
    with get_connection() as conn:
        result = _audit_cognitive_operations(
            document_id=document_id,
            query=query,
            planned_output=planned_output,
            conn=conn,
        )
        return result.model_dump()


@mcp.tool()
def detect_inference_violations(text: str) -> dict[str, Any]:
    """
    Scan text for inferential connectors and prohibited abstract nouns.

    Detects: therefore, thus, implies, means that, ontology, mechanism, structure.
    These signal unauthorized cognitive operations.

    Args:
        text: The text to scan for inference violations.

    Returns:
        Inference violation detection result.
    """
    result = _detect_inference_violations(text=text)
    return result.model_dump()


@mcp.tool()
def get_permitted_operations(segment_id: int) -> dict[str, Any]:
    """
    Get permitted cognitive operations based on text genre.

    Different genres allow different operations (narrative, poetry, wisdom, etc.).

    Args:
        segment_id: ID of the segment to check.

    Returns:
        Permitted operations result.
    """
    with get_connection() as conn:
        result = _get_permitted_operations(segment_id=segment_id, conn=conn)
        return result.model_dump()


@mcp.tool()
def generate_safe_fallback(
    question_type: str,
    document_title: str,
) -> dict[str, Any]:
    """
    Generate a safe, compliant response when query requires unauthorized operations.

    Use when audit_cognitive_operations returns violations.

    Args:
        question_type: Type of unauthorized operation (synthesis, explanation, etc.).
        document_title: Title of the document for the fallback message.

    Returns:
        Safe fallback response.
    """
    result = _generate_safe_fallback(
        question_type=question_type, document_title=document_title
    )
    return result.model_dump()


# =============================================================================
# Vocabulary Tools
# =============================================================================


@mcp.tool()
def build_document_vocabulary(document_id: int) -> dict[str, Any]:
    """
    Build closed vocabulary from document.

    Creates lexicon of all tokens. Required before using validate_output_vocabulary.

    Args:
        document_id: ID of the document to build vocabulary from.

    Returns:
        Vocabulary build result.
    """
    with get_connection() as conn:
        result = _build_document_vocabulary(document_id=document_id, conn=conn)
        return result.model_dump()


@mcp.tool()
def validate_output_vocabulary(document_id: int, output: str) -> dict[str, Any]:
    """
    Check if output uses only vocabulary present in the source document.

    Detects terms imported from outside the text.

    Args:
        document_id: ID of the document.
        output: The output text to validate against document vocabulary.

    Returns:
        Vocabulary validation result.
    """
    with get_connection() as conn:
        result = _validate_output_vocabulary(
            document_id=document_id, output=output, conn=conn
        )
        return result.model_dump()


# =============================================================================
# Literal Quote Validation
# =============================================================================


@mcp.tool()
def validate_literal_quote(
    quote: str,
    document_id: int | None = None,
    segment_id: int | None = None,
    fuzzy_threshold: float = 0.8,
) -> dict[str, Any]:
    """
    Verify that a quoted string exists EXACTLY in a segment or document.

    Use BEFORE claiming any text appears in the source.
    Returns confidence: "textual" (exact match), "partial" (similar), "not_found".
    Prevents pattern completion hallucination.

    Args:
        quote: The exact quote to validate.
        document_id: Optional: document to search.
        segment_id: Optional: specific segment to check.
        fuzzy_threshold: Similarity threshold for partial matches (0-1).

    Returns:
        Literal quote validation result.
    """
    with get_connection() as conn:
        result = _validate_literal_quote(
            quote=quote,
            conn=conn,
            document_id=document_id,
            segment_id=segment_id,
            fuzzy_threshold=fuzzy_threshold,
        )
        return result.model_dump()


# =============================================================================
# Proximity Validation
# =============================================================================


@mcp.tool()
def validate_proximity(
    base_segment_id: int,
    target_segment_id: int,
    max_distance: int = 1,
) -> dict[str, Any]:
    """
    Check if two segments are adjacent (within allowed distance).

    Use to enforce "same verse or verse+1" constraints.
    Prevents narrative jump violations.

    Args:
        base_segment_id: The anchor segment ID.
        target_segment_id: The segment ID being referenced.
        max_distance: Maximum allowed segment distance (0 = same, 1 = adjacent).

    Returns:
        Proximity validation result.
    """
    with get_connection() as conn:
        result = _validate_proximity(
            conn=conn,
            base_segment_id=base_segment_id,
            target_segment_id=target_segment_id,
            max_distance=max_distance,
        )
        return result  # Already a dict


@mcp.tool()
def get_adjacent_segments(
    base_segment_id: int,
    max_distance: int = 1,
) -> dict[str, Any]:
    """
    Get list of segment IDs within proximity constraint.

    Use for extraction queries that require adjacency.

    Args:
        base_segment_id: The anchor segment ID.
        max_distance: Maximum distance from base (default: 1).

    Returns:
        Adjacent segment IDs.
    """
    with get_connection() as conn:
        segment_ids = _get_adjacent_segment_ids(
            base_segment_id=base_segment_id, max_distance=max_distance, conn=conn
        )
        return {"base_segment_id": base_segment_id, "adjacent_ids": segment_ids}


# =============================================================================
# Speaker Identification
# =============================================================================


@mcp.tool()
def identify_speaker(
    segment_id: int,
    priority_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    expected_speaker: str | None = None,
) -> dict[str, Any]:
    """
    Identify who is speaking in a text segment.

    Returns speaker name, confidence level, and evidence.
    Domain-agnostic: works for any document type.

    Args:
        segment_id: ID of the segment to analyze.
        priority_patterns: Optional: Speaker names to prioritize.
        exclude_patterns: Optional: Speaker patterns to flag as ambiguous.
        expected_speaker: Optional: verify this specific speaker.

    Returns:
        Speaker identification result.
    """
    with get_connection() as conn:
        segment = get_segment_by_id(conn, segment_id)
        if not segment:
            return {"error": f"Segment {segment_id} not found"}
        result = _identify_speaker(
            content=segment["content"],
            priority_patterns=priority_patterns,
            exclude_patterns=exclude_patterns,
            expected_speaker=expected_speaker,
        )
        return result.model_dump()


# =============================================================================
# Pattern Contamination Detection
# =============================================================================


@mcp.tool()
def detect_pattern_contamination(
    claimed_output: str,
    segment_id: int,
    patterns: list[dict] | None = None,
) -> dict[str, Any]:
    """
    Detect when output may be completing a known pattern not in source.

    Domain-agnostic: works for any genre (religious, fairy tales, legal, etc.).
    Agent provides patterns dynamically based on document genre.

    Args:
        claimed_output: What the agent claims is in the text.
        segment_id: ID of the segment to check against.
        patterns: Optional: Pattern definitions with trigger/expectedCompletion.

    Returns:
        Pattern contamination detection result.
    """
    with get_connection() as conn:
        result = _detect_pattern_contamination(
            claimed_output=claimed_output,
            segment_id=segment_id,
            conn=conn,
            patterns=patterns,
        )
        return result.model_dump()


# =============================================================================
# Extraction Schema Validation
# =============================================================================


@mcp.tool()
def validate_extraction_schema(
    output: str,
    fields: list[str],
    allow_commentary: bool = False,
) -> dict[str, Any]:
    """
    Validate that extraction output follows a strict schema.

    Detects parenthetical comments, notes sections, evaluative language.
    Use when user requests pure data extraction.

    Args:
        output: The extraction output to validate.
        fields: Expected field names in output.
        allow_commentary: Whether commentary is allowed (default: False).

    Returns:
        Extraction schema validation result.
    """
    result = _validate_extraction_schema(
        output=output, fields=fields, allow_commentary=allow_commentary
    )
    return result.model_dump()


# =============================================================================
# Narrative Voice Detection
# =============================================================================


@mcp.tool()
def detect_narrative_voice(
    segment_id: int,
    domain_vocabulary: dict | None = None,
) -> dict[str, Any]:
    """
    CRITICAL: Detect the narrative voice type of a text segment.

    Distinguishes:
    - primary_narration ("The Lord did X") = action executed in-scene
    - human_to_divine ("You led them...") = human prayer/praise, RETROSPECTIVE
    - divine_direct_speech ("I am the Lord") = God speaking
    - human_about_divine ("The Lord is my shepherd") = descriptive

    Use BEFORE extracting "divine actions" to avoid confusing retrospective prayer
    with primary divine agency.

    Args:
        segment_id: ID of the segment to analyze.
        domain_vocabulary: Optional DomainVocabulary for enhanced detection.

    Returns:
        Narrative voice detection result.
    """
    vocab = None
    if domain_vocabulary:
        vocab = DomainVocabulary.model_validate(domain_vocabulary)

    with get_connection() as conn:
        segment = get_segment_by_id(conn, segment_id)
        if not segment:
            return {"error": f"Segment {segment_id} not found"}
        result = _detect_narrative_voice(
            content=segment["content"], vocabulary=vocab
        )
        return result.model_dump()


# =============================================================================
# Agency Execution Validation
# =============================================================================


@mcp.tool()
def validate_agency_execution(
    segment_id: int,
    divine_agent_patterns: list[str] | None = None,
) -> dict[str, Any]:
    """
    Validates whether a divine action is EXECUTED in-scene vs merely REFERENCED.

    Key distinction:
    - EXECUTED = "Fire came up from the rock" (Judges 6:21)
    - REFERENCED = "You led them with a pillar" (Nehemiah 9:12) - retrospective

    The second describes same action but as human memory, NOT primary execution.

    Args:
        segment_id: ID of the segment to analyze.
        divine_agent_patterns: Optional: Patterns to identify divine agent.

    Returns:
        Agency execution validation result.
    """
    with get_connection() as conn:
        segment = get_segment_by_id(conn, segment_id)
        if not segment:
            return {"error": f"Segment {segment_id} not found"}
        result = _validate_agency_execution(
            content=segment["content"], agent_patterns=divine_agent_patterns
        )
        return result.model_dump()


# =============================================================================
# Text Genre Detection
# =============================================================================


@mcp.tool()
def detect_text_genre(
    segment_id: int,
    domain_vocabulary: dict | None = None,
) -> dict[str, Any]:
    """
    Detect text genre to apply correct extraction rules.

    Genres: historical_narrative, narrative_poetry, prayer_praise,
    recapitulation, prophetic.

    DOMAIN-AGNOSTIC: Uses structural patterns by default.
    Provide domainVocabulary for domain-specific enhanced detection.

    Args:
        segment_id: ID of the segment to analyze.
        domain_vocabulary: Optional DomainVocabulary for enhanced detection.

    Returns:
        Text genre detection result.
    """
    vocab = None
    if domain_vocabulary:
        vocab = DomainVocabulary.model_validate(domain_vocabulary)

    with get_connection() as conn:
        segment = get_segment_by_id(conn, segment_id)
        if not segment:
            return {"error": f"Segment {segment_id} not found"}
        result = _detect_text_genre(content=segment["content"], vocabulary=vocab)
        return result.model_dump()


# =============================================================================
# Divine Agency Without Speech
# =============================================================================


@mcp.tool()
def detect_divine_agency_without_speech(
    segment_id: int,
    agent_patterns: list[str] | None = None,
    domain_vocabulary: dict | None = None,
) -> dict[str, Any]:
    """
    CRITICAL: Detect when an agent acts WITHOUT speaking.

    DOMAIN-AGNOSTIC: Agent provides agentPatterns dynamically.
    Separates SPEECH verbs (said, spoke) from ACTION verbs (caused, made, remembered).

    Examples:
    - Biblical ["God", "Lord"] finds "God remembered Noah"
    - Legal ["the Court"] finds "the Court ruled"

    Args:
        segment_id: ID of the segment to analyze.
        agent_patterns: Agent names to search for.
        domain_vocabulary: Optional DomainVocabulary for genre detection.

    Returns:
        Divine agency without speech detection result.
    """
    vocab = None
    if domain_vocabulary:
        vocab = DomainVocabulary.model_validate(domain_vocabulary)

    with get_connection() as conn:
        segment = get_segment_by_id(conn, segment_id)
        if not segment:
            return {"error": f"Segment {segment_id} not found"}
        result = _detect_divine_agency_without_speech(
            content=segment["content"],
            agent_patterns=agent_patterns,
            vocabulary=vocab,
        )
        return result  # Already a dict


# =============================================================================
# Weak Quantifier Detection
# =============================================================================


@mcp.tool()
def detect_weak_quantifiers(text: str) -> dict[str, Any]:
    """
    Detects weak quantifiers that require statistical evidence.

    Quantifiers like "frequently", "typically", "always", "never" imply
    statistical claims that should not be made without counting evidence.

    Returns recommendation: "allow", "require_count", or "block".
    Use on agent output BEFORE returning to user.

    Args:
        text: Text to analyze (typically agent output).

    Returns:
        Weak quantifier detection result.
    """
    result = _detect_weak_quantifiers(text=text)
    return result.model_dump()


# =============================================================================
# Existential Response Validation
# =============================================================================


@mcp.tool()
def validate_existential_response(response: str) -> dict[str, Any]:
    """
    CRITICAL: Validates response to existential question ("Does X exist in text?").

    VALID: "YES" + textual evidence, OR "NO" + explicit denial.
    INVALID: meta-discourse, hedging, questions, introducing categories not asked.

    Use AFTER generating response to existential questions to catch evasion.

    Args:
        response: The agent response to validate.

    Returns:
        Existential response validation result.
    """
    result = _validate_existential_response(response=response)
    return result.model_dump()


# =============================================================================
# DeltaCodeCube Tools
# =============================================================================


@mcp.tool()
def cube_index_file(path: str) -> dict[str, Any]:
    """
    Index a code file into the DeltaCodeCube.

    Extracts lexical, structural, and semantic features and stores
    the file as a point in 63-dimensional feature space.

    Args:
        path: Absolute path to the code file.

    Returns:
        CodePoint information including position in cube.
    """
    with get_connection() as conn:
        cube = DeltaCodeCube(conn)
        code_point = cube.index_file(path)
        return code_point.to_dict()


@mcp.tool()
def cube_index_directory(
    path: str,
    patterns: list[str] | None = None,
    recursive: bool = True,
) -> dict[str, Any]:
    """
    Index all code files in a directory.

    Args:
        path: Absolute path to directory.
        patterns: Glob patterns for files (default: js, ts, py, go, java).
        recursive: Whether to search recursively (default: True).

    Returns:
        Summary of indexed files.
    """
    with get_connection() as conn:
        cube = DeltaCodeCube(conn)
        code_points = cube.index_directory(path, patterns, recursive)

        return {
            "indexed_count": len(code_points),
            "files": [
                {
                    "path": cp.file_path,
                    "domain": cp.dominant_domain,
                    "lines": cp.line_count,
                }
                for cp in code_points
            ],
        }


@mcp.tool()
def cube_get_position(path: str) -> dict[str, Any]:
    """
    Get the position of a code file in the DeltaCodeCube.

    Returns the file's coordinates in the 63-dimensional feature space,
    broken down by lexical, structural, and semantic components.

    Args:
        path: Absolute path to the code file.

    Returns:
        Position information including feature vectors and dominant domain.
    """
    with get_connection() as conn:
        cube = DeltaCodeCube(conn)
        position = cube.get_position(path)

        if not position:
            return {"error": f"File not indexed: {path}"}

        return position


@mcp.tool()
def cube_find_similar(
    path: str,
    limit: int = 5,
    axis: str | None = None,
) -> dict[str, Any]:
    """
    Find code files similar to a given file.

    Searches for files with closest positions in the feature space.
    Can optionally search in a specific axis only.

    Args:
        path: Absolute path to reference file.
        limit: Maximum results to return (default: 5).
        axis: Specific axis to compare ('lexical', 'structural', 'semantic', or None for all).

    Returns:
        List of similar files with distances and similarity scores.
    """
    with get_connection() as conn:
        cube = DeltaCodeCube(conn)
        results = cube.find_similar(path, limit, axis)

        if not results:
            return {"error": f"File not indexed or no similar files found: {path}"}

        return {"similar_files": results}


@mcp.tool()
def cube_search_by_domain(domain: str, limit: int = 10) -> dict[str, Any]:
    """
    Find code files by semantic domain.

    Searches for files classified in a specific functional domain.

    Args:
        domain: Domain name ('auth', 'db', 'api', 'ui', 'util').
        limit: Maximum results (default: 10).

    Returns:
        List of files in the specified domain.
    """
    with get_connection() as conn:
        cube = DeltaCodeCube(conn)
        results = cube.search_by_domain(domain, limit)
        return {"files": results, "domain": domain, "count": len(results)}


@mcp.tool()
def cube_get_stats() -> dict[str, Any]:
    """
    Get statistics about the DeltaCodeCube.

    Returns counts of indexed files, lines of code, and distribution by domain.

    Returns:
        Cube statistics.
    """
    with get_connection() as conn:
        cube = DeltaCodeCube(conn)
        return cube.get_stats()


@mcp.tool()
def cube_list_code_points(limit: int = 100, offset: int = 0) -> dict[str, Any]:
    """
    List all indexed code points.

    Args:
        limit: Maximum results (default: 100).
        offset: Offset for pagination (default: 0).

    Returns:
        List of code point summaries.
    """
    with get_connection() as conn:
        cube = DeltaCodeCube(conn)
        code_points = cube.list_code_points(limit, offset)
        return {"code_points": code_points, "count": len(code_points)}


@mcp.tool()
def cube_get_contracts(
    path: str | None = None,
    direction: str = "both",
    limit: int = 100,
) -> dict[str, Any]:
    """
    Get contracts (dependencies) between code files.

    A contract represents an import/require relationship between two files.
    Each contract includes a baseline_distance that represents the "healthy"
    distance between caller and callee in the 63D feature space.

    Args:
        path: Optional file path to filter contracts for a specific file.
        direction: Filter direction when path is provided:
                  - 'incoming': Files that import this file (dependents)
                  - 'outgoing': Files this file imports (dependencies)
                  - 'both': All contracts involving this file (default)
        limit: Maximum contracts to return (default: 100).

    Returns:
        Contract list with caller/callee info and baseline distances.
    """
    with get_connection() as conn:
        cube = DeltaCodeCube(conn)
        contracts = cube.get_contracts(file_path=path, direction=direction, limit=limit)
        return {"contracts": contracts, "count": len(contracts)}


@mcp.tool()
def cube_get_contract_stats() -> dict[str, Any]:
    """
    Get statistics about detected contracts.

    Returns total contracts, breakdown by type, and distance statistics.

    Returns:
        Contract statistics.
    """
    with get_connection() as conn:
        cube = DeltaCodeCube(conn)
        return cube.get_contract_stats()


# =============================================================================
# Phase 3: Delta and Tension Tools
# =============================================================================


@mcp.tool()
def cube_reindex(path: str) -> dict[str, Any]:
    """
    Re-index a file and detect changes (deltas) and tensions.

    When a code file changes, this tool:
    1. Compares the new code with the previously indexed version
    2. Creates a Delta recording the movement in 63D feature space
    3. Detects any Tensions (contracts that may be broken)
    4. Updates the CodePoint in the database

    Use this after modifying a file to see what impact the changes have.

    Args:
        path: Absolute path to the file that changed.

    Returns:
        Reindex result with delta and detected tensions.
    """
    with get_connection() as conn:
        cube = DeltaCodeCube(conn)
        return cube.reindex_file(path)


@mcp.tool()
def cube_analyze_impact(path: str) -> dict[str, Any]:
    """
    Analyze potential impact if a file were to change.

    Shows all files that depend on this file (import it) and their
    current distances in the 63D feature space. Useful for:
    - Understanding dependencies before making changes
    - Identifying high-impact files
    - Planning refactoring

    Args:
        path: Absolute path to the file to analyze.

    Returns:
        Impact analysis with list of dependent files and their distances.
    """
    with get_connection() as conn:
        cube = DeltaCodeCube(conn)
        return cube.analyze_impact(path)


@mcp.tool()
def cube_get_tensions(
    status: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """
    Get detected tensions (potential contract violations).

    A Tension is created when a code file changes and its distance to
    dependent files deviates significantly from the baseline. This indicates
    the change may have broken implicit dependencies.

    Args:
        status: Filter by status:
               - 'detected': New tensions not yet reviewed
               - 'reviewed': Tensions that have been seen
               - 'resolved': Fixed tensions
               - 'ignored': Tensions marked as non-issues
               - None: All tensions (default)
        limit: Maximum tensions to return (default: 50).

    Returns:
        List of tensions with severity and suggested actions.
    """
    with get_connection() as conn:
        cube = DeltaCodeCube(conn)
        tensions = cube.get_tensions(status=status, limit=limit)
        stats = cube.get_tension_stats()
        return {
            "tensions": tensions,
            "count": len(tensions),
            "stats": stats,
        }


@mcp.tool()
def cube_resolve_tension(tension_id: str, status: str = "resolved") -> dict[str, Any]:
    """
    Update the status of a tension.

    After reviewing a tension, mark it as resolved, ignored, or reviewed.

    Args:
        tension_id: ID of the tension to update.
        status: New status:
               - 'reviewed': Marked as seen but not yet fixed
               - 'resolved': Fixed and no longer an issue
               - 'ignored': Not a real issue, ignore it

    Returns:
        Update result.
    """
    with get_connection() as conn:
        cube = DeltaCodeCube(conn)
        success = cube.resolve_tension(tension_id, status)
        return {
            "success": success,
            "tension_id": tension_id,
            "new_status": status if success else None,
            "message": "Tension updated." if success else "Tension not found.",
        }


@mcp.tool()
def cube_get_deltas(limit: int = 20) -> dict[str, Any]:
    """
    Get recent code changes (deltas).

    Shows history of code movements in the 63D feature space.
    Each delta records what changed (lexical, structural, semantic)
    and by how much.

    Args:
        limit: Maximum deltas to return (default: 20).

    Returns:
        List of recent deltas with movement analysis.
    """
    with get_connection() as conn:
        cube = DeltaCodeCube(conn)
        deltas = cube.get_deltas(limit=limit)
        return {
            "deltas": deltas,
            "count": len(deltas),
        }

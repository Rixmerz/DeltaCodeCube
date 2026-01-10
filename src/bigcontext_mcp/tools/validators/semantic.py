"""Semantic frame detection tools."""

import re

from bigcontext_mcp.types import (
    SemanticFrameResult,
    SubdeterminationResult,
    PerformativeResult,
    AnachronismResult,
)


def detect_semantic_frames(
    content: str,
    query: str,
) -> SemanticFrameResult:
    """
    Detect conceptual frameworks in a text segment.

    Identifies:
    - Causal frames
    - Revelational frames
    - Performative frames
    - Invocative frames

    Args:
        content: Text content to analyze.
        query: The research question being investigated.

    Returns:
        SemanticFrameResult with detected frames.
    """
    content_lower = content.lower()
    query_lower = query.lower()

    frames: list[str] = []
    frame_evidence: dict[str, list[str]] = {}
    warnings: list[str] = []

    # Detect causal frame
    causal_markers = [
        "because", "therefore", "thus", "hence", "so that",
        "in order to", "caused", "resulted", "led to",
    ]
    causal_evidence = [m for m in causal_markers if m in content_lower]
    if causal_evidence:
        frames.append("causal")
        frame_evidence["causal"] = causal_evidence

    # Detect revelational frame (Johannine light/life categories)
    revelational_markers = [
        "light", "life", "truth", "way", "word",
        "logos", "glory", "spirit", "father", "son",
    ]
    revelational_evidence = [m for m in revelational_markers if m in content_lower]
    if len(revelational_evidence) >= 2:
        frames.append("revelational")
        frame_evidence["revelational"] = revelational_evidence

    # Detect performative frame (speech-acts)
    performative_markers = [
        "let there be", "and it was so", "god said",
        "the lord said", "thus says", "i am",
        "be it known", "hear, o",
    ]
    performative_evidence = [m for m in performative_markers if m in content_lower]
    if performative_evidence:
        frames.append("performative")
        frame_evidence["performative"] = performative_evidence

    # Detect invocative frame (prayer/worship)
    invocative_markers = [
        "o lord", "praise", "bless", "hallelujah",
        "holy", "worship", "glory to", "thanks be",
    ]
    invocative_evidence = [m for m in invocative_markers if m in content_lower]
    if invocative_evidence:
        frames.append("invocative")
        frame_evidence["invocative"] = invocative_evidence

    # Check for frame conflicts in query
    if "cause" in query_lower and "performative" in frames:
        warnings.append("Query uses causal language but text uses performative frame")
    if "mechanism" in query_lower and "revelational" in frames:
        warnings.append("Query seeks mechanism but text uses revelational categories")

    dominant_frame = frames[0] if frames else None

    return SemanticFrameResult(
        frames=frames,
        dominant_frame=dominant_frame,
        frame_evidence=frame_evidence,
        warnings=warnings,
    )


def analyze_subdetermination(
    content: str,
) -> SubdeterminationResult:
    """
    Analyze whether textual ambiguity is total indeterminacy or directed subdetermination.

    Returns what the text CLOSES (excludes) vs. what it LEAVES OPEN.

    Args:
        content: Text content to analyze.

    Returns:
        SubdeterminationResult with analysis.
    """
    content_lower = content.lower()

    # What the text closes (definite assertions)
    closed: list[str] = []
    left_open: list[str] = []
    asymmetric_relations: list[str] = []

    # Detect definite assertions (closed)
    definite_patterns = [
        (r"\bis\b", "identity assertion"),
        (r"\bwas\b", "past state assertion"),
        (r"\bshall\b", "future assertion"),
        (r"\bmust\b", "necessity assertion"),
        (r"\bnot\b", "negation"),
    ]
    for pattern, desc in definite_patterns:
        if re.search(pattern, content_lower):
            closed.append(desc)

    # Detect open-ended elements
    open_patterns = [
        (r"\blike\b", "simile - comparison open"),
        (r"\bas\b", "analogy - mapping open"),
        (r"\bmystery\b", "explicit mystery"),
        (r"\b(who|what|how|why)\b", "interrogative - answer open"),
    ]
    for pattern, desc in open_patterns:
        if re.search(pattern, content_lower):
            left_open.append(desc)

    # Detect asymmetric relations (A > B but not B > A)
    asymmetric_patterns = [
        (r"god.{1,20}created", "God→creation (unidirectional)"),
        (r"father.{1,20}son", "Father→Son (asymmetric origin)"),
        (r"(sent|gave).{1,20}(son|him)", "Sender→Sent (asymmetric mission)"),
    ]
    for pattern, desc in asymmetric_patterns:
        if re.search(pattern, content_lower):
            asymmetric_relations.append(desc)

    # Determine if truly indeterminate or subdetermined
    is_indeterminate = len(closed) == 0 and len(left_open) > 3
    is_subdetermined = len(closed) > 0 and len(left_open) > 0

    return SubdeterminationResult(
        closed=closed,
        left_open=left_open,
        asymmetric_relations=asymmetric_relations,
        is_indeterminate=is_indeterminate,
        is_subdetermined=is_subdetermined,
    )


def detect_performatives(
    content: str,
) -> PerformativeResult:
    """
    Detect performative speech acts where divine speech IS the creative act.

    Identifies "And God said... and it was so" patterns that resist causal analysis.

    Args:
        content: Text content to analyze.

    Returns:
        PerformativeResult with detected performatives.
    """
    content_lower = content.lower()

    performatives: list[dict] = []

    # Pattern: "And X said... and it was/there was"
    speech_effect_pattern = re.compile(
        r"(and\s+)?(\w+)\s+said[,:]?\s*[\"']?(.{10,100}?)[\"']?\s*"
        r"(and\s+(it\s+was\s+so|there\s+was|it\s+was))",
        re.IGNORECASE | re.DOTALL
    )

    for match in speech_effect_pattern.finditer(content):
        performatives.append({
            "speaker": match.group(2),
            "speech": match.group(3)[:50],
            "effect": match.group(4),
            "type": "speech-act creation",
        })

    # Pattern: "Let there be X"
    let_pattern = re.compile(r"let there be\s+(\w+)", re.IGNORECASE)
    for match in let_pattern.finditer(content):
        performatives.append({
            "speaker": "implied",
            "speech": match.group(0),
            "effect": match.group(1),
            "type": "fiat creation",
        })

    # Pattern: Naming performatives
    naming_pattern = re.compile(
        r"(called|named)\s+(the\s+)?(\w+)\s+[\"']?(\w+)[\"']?",
        re.IGNORECASE
    )
    for match in naming_pattern.finditer(content):
        performatives.append({
            "speaker": "implied",
            "speech": match.group(0),
            "effect": f"naming of {match.group(3)}",
            "type": "naming performative",
        })

    has_performatives = len(performatives) > 0
    resists_causal_analysis = has_performatives and any(
        p["type"] == "speech-act creation" for p in performatives
    )

    return PerformativeResult(
        performatives=performatives,
        has_performatives=has_performatives,
        resists_causal_analysis=resists_causal_analysis,
    )


def check_anachronisms(
    query: str,
) -> AnachronismResult:
    """
    Check if a research question imports post-biblical conceptual categories.

    Detects Aristotelian causes, Neoplatonic emanation, Trinitarian doctrine, etc.

    Args:
        query: The research question or claim to check.

    Returns:
        AnachronismResult with detected anachronisms.
    """
    query_lower = query.lower()

    anachronisms: list[dict] = []

    # Aristotelian categories
    aristotelian_terms = [
        ("efficient cause", "Aristotelian four causes"),
        ("final cause", "Aristotelian four causes"),
        ("material cause", "Aristotelian four causes"),
        ("formal cause", "Aristotelian four causes"),
        ("substance", "Aristotelian metaphysics"),
        ("essence", "Aristotelian metaphysics"),
        ("accident", "Aristotelian categories"),
        ("potentiality", "Aristotelian metaphysics"),
        ("actuality", "Aristotelian metaphysics"),
    ]

    # Neoplatonic categories
    neoplatonic_terms = [
        ("emanation", "Neoplatonic cosmology"),
        ("the one", "Neoplatonic henology"),
        ("nous", "Neoplatonic hierarchy"),
        ("world soul", "Neoplatonic hierarchy"),
        ("procession", "Neoplatonic emanation"),
        ("return", "Neoplatonic return"),
    ]

    # Post-Nicene Trinitarian
    trinitarian_terms = [
        ("trinity", "Post-Nicene doctrine (325 CE+)"),
        ("trinitarian", "Post-Nicene doctrine"),
        ("consubstantial", "Nicene Creed (325 CE)"),
        ("homoousios", "Nicene terminology"),
        ("hypostasis", "Cappadocian terminology (4th century)"),
        ("perichoresis", "Late patristic (6th century+)"),
        ("eternal generation", "Post-Nicene development"),
    ]

    # Modern theological
    modern_terms = [
        ("ontology", "Modern philosophical category"),
        ("metaphysics", "Post-Aristotelian category"),
        ("systematic", "Modern theological method"),
        ("hermeneutics", "Modern interpretive theory"),
    ]

    all_terms = aristotelian_terms + neoplatonic_terms + trinitarian_terms + modern_terms

    for term, framework in all_terms:
        if term in query_lower:
            anachronisms.append({
                "term": term,
                "framework": framework,
                "risk": "May distort text-internal meaning",
            })

    has_anachronisms = len(anachronisms) > 0

    recommendation: str | None = None
    if has_anachronisms:
        frameworks = set(a["framework"].split()[0] for a in anachronisms)
        recommendation = f"Consider reformulating query without {', '.join(frameworks)} terminology"

    return AnachronismResult(
        anachronisms=anachronisms,
        has_anachronisms=has_anachronisms,
        recommendation=recommendation,
    )

"""
Lexical feature extractor for code files.

Extracts TF-IDF based features projected to a fixed vocabulary.
Returns 50 dimensions representing term importance scores.
"""

import re
from collections import Counter
from typing import Any

import numpy as np

# Feature dimension
LEXICAL_DIMS = 50

# Default vocabulary of important code terms
# This can be dynamically updated based on corpus
DEFAULT_VOCABULARY = [
    # Common programming terms
    "function",
    "class",
    "const",
    "let",
    "var",
    "return",
    "async",
    "await",
    "import",
    "export",
    "default",
    "module",
    "require",
    # Control flow
    "if",
    "else",
    "for",
    "while",
    "switch",
    "case",
    "break",
    "continue",
    "try",
    "catch",
    "throw",
    "finally",
    # Data types and structures
    "string",
    "number",
    "boolean",
    "array",
    "object",
    "null",
    "undefined",
    "true",
    "false",
    "map",
    "set",
    "list",
    "dict",
    # OOP
    "this",
    "self",
    "new",
    "constructor",
    "extends",
    "super",
    "static",
    "private",
    "public",
    "protected",
    # Common operations
    "get",
    "set",
    "add",
    "remove",
    "update",
    "delete",
    "create",
    "find",
    "filter",
    "reduce",
    # Error handling
    "error",
    "exception",
    "message",
    "status",
    "code",
    # Async patterns
    "promise",
    "callback",
    "then",
    "resolve",
    "reject",
    # Common identifiers
    "data",
    "result",
    "response",
    "request",
    "config",
    "options",
    "params",
    "args",
    "value",
    "key",
    "index",
    "item",
    "name",
    "type",
    "id",
]

# Ensure we have exactly LEXICAL_DIMS terms
_vocab = DEFAULT_VOCABULARY[:LEXICAL_DIMS]
while len(_vocab) < LEXICAL_DIMS:
    _vocab.append(f"term_{len(_vocab)}")

VOCABULARY = _vocab


def extract_lexical_features(
    content: str,
    vocabulary: list[str] | None = None,
) -> np.ndarray:
    """
    Extract lexical features from code content.

    Calculates term frequency for vocabulary terms and normalizes.

    Args:
        content: Source code content as string.
        vocabulary: Optional custom vocabulary. Uses default if not provided.

    Returns:
        NumPy array of 50 normalized TF scores.
    """
    vocab = vocabulary or VOCABULARY

    # Ensure vocabulary has correct size
    if len(vocab) != LEXICAL_DIMS:
        vocab = vocab[:LEXICAL_DIMS]
        while len(vocab) < LEXICAL_DIMS:
            vocab.append(f"term_{len(vocab)}")

    # Tokenize content (extract words)
    tokens = _tokenize(content)

    # Count term frequencies
    term_counts = Counter(tokens)
    total_terms = len(tokens) or 1

    # Build feature vector
    features = np.zeros(LEXICAL_DIMS, dtype=np.float64)

    for i, term in enumerate(vocab):
        count = term_counts.get(term.lower(), 0)
        # Term frequency (normalized by document length)
        tf = count / total_terms
        features[i] = tf

    # L2 normalize the vector
    norm = np.linalg.norm(features)
    if norm > 0:
        features = features / norm

    return features


def _tokenize(content: str) -> list[str]:
    """
    Tokenize code content into terms.

    Handles camelCase, snake_case, and regular words.
    """
    # Convert camelCase to separate words
    content = re.sub(r"([a-z])([A-Z])", r"\1 \2", content)

    # Convert snake_case to separate words
    content = content.replace("_", " ")

    # Extract words (letters only, 2+ chars)
    words = re.findall(r"\b[a-zA-Z]{2,}\b", content.lower())

    return words


def get_vocabulary() -> list[str]:
    """Return the current vocabulary list."""
    return VOCABULARY.copy()


def build_vocabulary_from_corpus(contents: list[str], top_n: int = LEXICAL_DIMS) -> list[str]:
    """
    Build vocabulary from a corpus of code files.

    Args:
        contents: List of code file contents.
        top_n: Number of top terms to include.

    Returns:
        List of most frequent terms across corpus.
    """
    all_terms: Counter[str] = Counter()

    for content in contents:
        tokens = _tokenize(content)
        all_terms.update(tokens)

    # Get top N terms
    most_common = all_terms.most_common(top_n)
    return [term for term, _ in most_common]


def get_term_scores(features: np.ndarray, vocabulary: list[str] | None = None) -> dict[str, float]:
    """
    Get term scores as dictionary.

    Args:
        features: Lexical feature vector (50 dimensions).
        vocabulary: Vocabulary list to use.

    Returns:
        Dictionary mapping terms to scores.
    """
    vocab = vocabulary or VOCABULARY
    return {vocab[i]: float(features[i]) for i in range(min(len(vocab), len(features)))}


def get_top_terms(features: np.ndarray, n: int = 10, vocabulary: list[str] | None = None) -> list[tuple[str, float]]:
    """
    Get top N terms by score.

    Args:
        features: Lexical feature vector.
        n: Number of top terms to return.
        vocabulary: Vocabulary list to use.

    Returns:
        List of (term, score) tuples sorted by score descending.
    """
    vocab = vocabulary or VOCABULARY
    term_scores = [(vocab[i], float(features[i])) for i in range(min(len(vocab), len(features)))]
    term_scores.sort(key=lambda x: x[1], reverse=True)
    return term_scores[:n]

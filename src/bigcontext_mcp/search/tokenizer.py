"""Text tokenization for search indexing."""

import re
from dataclasses import dataclass

from bigcontext_mcp.search.stopwords import is_stop_word


@dataclass
class TokenizeOptions:
    """Options for tokenization."""

    lowercase: bool = True
    remove_stop_words: bool = True
    min_length: int = 2
    max_length: int = 50
    stemming: bool = False


def tokenize(text: str, options: TokenizeOptions | None = None) -> list[str]:
    """Tokenize text into words."""
    opts = options or TokenizeOptions()

    # Normalize text
    normalized = text
    if opts.lowercase:
        normalized = normalized.lower()

    # Remove punctuation except apostrophes in contractions
    normalized = re.sub(r"[^\w\s'-]", " ", normalized)
    normalized = re.sub(r"--+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = normalized.strip()

    # Split into words
    words = [w for w in normalized.split() if w]

    # Apply filters
    filtered_words = []
    for word in words:
        # Check length constraints
        if len(word) < opts.min_length or len(word) > opts.max_length:
            continue

        # Check if it's a number only
        if word.isdigit():
            continue

        # Remove stop words if enabled
        if opts.remove_stop_words and is_stop_word(word):
            continue

        filtered_words.append(word)

    # Apply basic stemming if enabled
    if opts.stemming:
        filtered_words = [_simple_stem(w) for w in filtered_words]

    return filtered_words


def _simple_stem(word: str) -> str:
    """Simple stemming - removes common suffixes."""
    # English suffixes
    suffixes = ["ing", "ed", "es", "s", "ment", "ness", "tion", "ation", "ly", "er", "est"]

    for suffix in suffixes:
        if word.endswith(suffix) and len(word) > len(suffix) + 2:
            return word[: -len(suffix)]

    return word


def count_term_frequencies(
    text: str, options: TokenizeOptions | None = None
) -> dict[str, int]:
    """Count term frequencies in text."""
    tokens = tokenize(text, options)
    frequencies: dict[str, int] = {}

    for token in tokens:
        frequencies[token] = frequencies.get(token, 0) + 1

    return frequencies


def get_top_terms(
    frequencies: dict[str, int], n: int
) -> list[dict[str, int | str]]:
    """Get top N terms by frequency."""
    sorted_terms = sorted(frequencies.items(), key=lambda x: x[1], reverse=True)
    return [{"term": term, "count": count} for term, count in sorted_terms[:n]]

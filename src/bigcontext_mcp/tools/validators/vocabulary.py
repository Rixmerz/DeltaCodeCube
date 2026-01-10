"""Vocabulary validation tools."""

import re
import sqlite3
from collections import Counter

from bigcontext_mcp.db.queries import get_document_by_id
from bigcontext_mcp.types import VocabularyBuildResult, VocabularyValidationResult


def build_document_vocabulary(
    document_id: int,
    conn: sqlite3.Connection,
) -> VocabularyBuildResult:
    """
    Build closed vocabulary from document.

    Creates lexicon of all tokens in document.

    Args:
        document_id: ID of the document to build vocabulary from.
        conn: Database connection.

    Returns:
        VocabularyBuildResult with vocabulary statistics.
    """
    doc = get_document_by_id(conn, document_id)
    if not doc:
        return VocabularyBuildResult(
            document_id=document_id,
            vocabulary_size=0,
            vocabulary=[],
            top_terms=[],
        )

    content = doc.get("content", "") or ""

    # Tokenize
    tokens = re.findall(r"\b[a-zA-Z]+\b", content.lower())

    # Count frequencies
    term_counts = Counter(tokens)

    # Get unique vocabulary
    vocabulary = list(term_counts.keys())

    # Get top terms
    top_terms = [{"term": term, "count": count} for term, count in term_counts.most_common(50)]

    return VocabularyBuildResult(
        document_id=document_id,
        vocabulary_size=len(vocabulary),
        vocabulary=vocabulary[:1000],  # Limit for response size
        top_terms=top_terms,
    )


def validate_output_vocabulary(
    document_id: int,
    output: str,
    conn: sqlite3.Connection,
) -> VocabularyValidationResult:
    """
    Check if output uses only vocabulary present in the source document.

    Detects terms imported from outside the text.

    Args:
        document_id: ID of the document.
        output: The output text to validate against document vocabulary.
        conn: Database connection.

    Returns:
        VocabularyValidationResult with validation status.
    """
    # Build vocabulary
    vocab_result = build_document_vocabulary(document_id, conn)
    doc_vocabulary = set(vocab_result.vocabulary)

    # Tokenize output
    output_tokens = re.findall(r"\b[a-zA-Z]+\b", output.lower())
    output_vocabulary = set(output_tokens)

    # Find imported terms
    imported_terms = output_vocabulary - doc_vocabulary

    # Filter out common English words that might reasonably appear
    common_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "must", "shall", "can",
        "this", "that", "these", "those", "it", "its", "they", "them",
        "we", "us", "you", "your", "i", "my", "me", "he", "she", "him",
        "her", "his", "hers", "and", "or", "but", "if", "then", "else",
        "when", "where", "what", "which", "who", "whom", "whose", "how",
        "why", "not", "no", "yes", "all", "any", "some", "none", "each",
        "every", "either", "neither", "both", "few", "many", "more",
        "most", "other", "such", "only", "own", "same", "so", "than",
        "too", "very", "just", "also", "now", "here", "there", "then",
        "about", "above", "after", "again", "against", "before", "below",
        "between", "during", "from", "into", "through", "under", "until",
        "with", "within", "without", "for", "of", "on", "to", "by", "at",
        "in", "as",
    }

    # Actual foreign terms (not in document and not common English)
    foreign_terms = imported_terms - common_words

    is_valid = len(foreign_terms) == 0

    # Calculate contamination percentage
    if output_vocabulary:
        contamination_percentage = len(foreign_terms) / len(output_vocabulary) * 100
    else:
        contamination_percentage = 0.0

    return VocabularyValidationResult(
        is_valid=is_valid,
        imported_terms=list(foreign_terms)[:50],  # Limit response size
        contamination_percentage=round(contamination_percentage, 2),
        total_output_terms=len(output_vocabulary),
        document_vocabulary_size=len(doc_vocabulary),
    )

"""Search module with TF-IDF implementation."""

from bigcontext_mcp.search.stopwords import (
    ALL_STOPWORDS,
    ENGLISH_STOPWORDS,
    SPANISH_STOPWORDS,
    filter_stop_words,
    is_stop_word,
)
from bigcontext_mcp.search.tfidf import (
    cosine_similarity,
    generate_snippet,
    get_segment_vector,
    get_top_terms_by_tfidf,
    index_segment,
    rebuild_idf,
    search,
)
from bigcontext_mcp.search.tokenizer import (
    TokenizeOptions,
    count_term_frequencies,
    get_top_terms,
    tokenize,
)

__all__ = [
    # Stopwords
    "ENGLISH_STOPWORDS",
    "SPANISH_STOPWORDS",
    "ALL_STOPWORDS",
    "is_stop_word",
    "filter_stop_words",
    # Tokenizer
    "TokenizeOptions",
    "tokenize",
    "count_term_frequencies",
    "get_top_terms",
    # TF-IDF
    "index_segment",
    "rebuild_idf",
    "search",
    "generate_snippet",
    "get_segment_vector",
    "cosine_similarity",
    "get_top_terms_by_tfidf",
]

"""Stop words for English and Spanish."""

# Common English stop words
ENGLISH_STOPWORDS = frozenset([
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
    "to", "was", "were", "will", "with", "this", "but", "they",
    "have", "had", "what", "when", "where", "who", "which", "why", "how",
    "all", "each", "every", "both", "few", "more", "most", "other", "some",
    "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too",
    "very", "can", "just", "should", "now", "i", "me", "my", "myself", "we",
    "our", "ours", "ourselves", "you", "your", "yours", "yourself", "yourselves",
    "him", "his", "himself", "she", "her", "hers", "herself", "them", "their",
    "theirs", "themselves", "these", "those",
    "am", "been", "being", "do", "does", "did", "doing", "would", "could",
    "ought", "i'm", "you're", "he's", "she's", "it's", "we're", "they're",
    "i've", "you've", "we've", "they've", "i'd", "you'd", "he'd", "she'd",
    "we'd", "they'd", "i'll", "you'll", "he'll", "she'll", "we'll", "they'll",
    "isn't", "aren't", "wasn't", "weren't", "hasn't", "haven't", "hadn't",
    "doesn't", "don't", "didn't", "won't", "wouldn't", "shan't", "shouldn't",
    "can't", "cannot", "couldn't", "mustn't", "let's", "that's", "who's",
    "what's", "here's", "there's", "when's", "where's", "why's", "how's",
    "about", "above", "after", "again", "against", "below", "between", "into",
    "through", "during", "before", "under", "over", "once", "here", "there",
    "then", "out", "up", "down", "off", "further", "any", "or", "because",
    "until", "while", "if",
])

# Common Spanish stop words
SPANISH_STOPWORDS = frozenset([
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al",
    "a", "ante", "bajo", "con", "contra", "desde", "en", "entre", "hacia",
    "hasta", "para", "por", "segun", "sin", "sobre", "tras", "y", "e", "ni",
    "o", "u", "pero", "mas", "sino", "porque", "que", "quien", "cual", "cuyo",
    "donde", "cuando", "como", "si", "no", "muy", "mucho", "poco", "todo",
    "este", "esta", "estos", "estas", "ese", "esa", "esos", "esas", "aquel",
    "aquella", "yo", "tu", "ella", "nosotros", "vosotros", "ellos", "ellas",
    "me", "te", "se", "nos", "os", "lo", "le", "les", "mi", "su", "nuestro",
    "vuestro", "mio", "tuyo", "suyo", "ser", "estar", "haber", "tener", "hacer",
    "poder", "decir", "ir", "ver", "dar", "saber", "querer", "llegar", "pasar",
    "deber", "poner", "parecer", "quedar", "creer", "hablar", "llevar", "dejar",
    "seguir", "encontrar", "llamar", "venir", "pensar", "salir", "volver", "tomar",
    "conocer", "vivir", "sentir", "tratar", "mirar", "contar", "empezar", "esperar",
    "buscar", "existir", "entrar", "trabajar", "escribir", "perder", "producir",
    "ocurrir", "entender", "pedir", "recibir", "recordar", "terminar", "permitir",
    "aparecer", "conseguir", "comenzar", "servir", "sacar", "necesitar", "mantener",
    "resultar", "leer", "caer", "cambiar", "presentar", "crear", "abrir", "considerar",
])

# All stopwords combined
ALL_STOPWORDS = ENGLISH_STOPWORDS | SPANISH_STOPWORDS


def is_stop_word(word: str) -> bool:
    """Check if a word is a stop word."""
    return word.lower() in ALL_STOPWORDS


def filter_stop_words(words: list[str]) -> list[str]:
    """Filter out stop words from a list."""
    return [w for w in words if not is_stop_word(w)]

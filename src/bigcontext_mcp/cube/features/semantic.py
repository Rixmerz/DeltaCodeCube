"""
Semantic feature extractor for code files.

Classifies code by functional domain using keyword presence.
Returns 5 dimensions representing probability distribution across domains:
1. auth: Authentication, authorization, security
2. db: Database, queries, models
3. api: Routes, endpoints, HTTP
4. ui: Components, rendering, styles
5. util: Helpers, utilities, transformations
"""

import re
from typing import Any

import numpy as np

# Feature dimension
SEMANTIC_DIMS = 5

# Domain keywords for classification
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "auth": [
        "login",
        "logout",
        "password",
        "token",
        "session",
        "auth",
        "authenticate",
        "authorize",
        "jwt",
        "credential",
        "user",
        "permission",
        "role",
        "access",
        "security",
        "encrypt",
        "decrypt",
        "hash",
        "salt",
        "oauth",
        "sso",
        "2fa",
        "mfa",
        "verify",
        "signin",
        "signup",
    ],
    "db": [
        "query",
        "select",
        "insert",
        "update",
        "delete",
        "database",
        "model",
        "schema",
        "table",
        "column",
        "row",
        "migration",
        "seed",
        "sql",
        "nosql",
        "mongo",
        "postgres",
        "mysql",
        "redis",
        "orm",
        "repository",
        "entity",
        "transaction",
        "commit",
        "rollback",
        "index",
        "foreign",
        "primary",
        "constraint",
    ],
    "api": [
        "route",
        "router",
        "endpoint",
        "request",
        "response",
        "http",
        "rest",
        "graphql",
        "controller",
        "handler",
        "middleware",
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "api",
        "fetch",
        "axios",
        "cors",
        "header",
        "body",
        "param",
        "query",
        "status",
        "json",
        "webhook",
        "socket",
        "websocket",
    ],
    "ui": [
        "render",
        "component",
        "view",
        "style",
        "css",
        "scss",
        "click",
        "button",
        "form",
        "input",
        "modal",
        "dialog",
        "menu",
        "nav",
        "layout",
        "page",
        "screen",
        "widget",
        "element",
        "dom",
        "html",
        "jsx",
        "tsx",
        "template",
        "props",
        "state",
        "hook",
        "effect",
        "ref",
        "context",
        "redux",
        "store",
    ],
    "util": [
        "helper",
        "util",
        "utils",
        "format",
        "parse",
        "convert",
        "transform",
        "validate",
        "sanitize",
        "escape",
        "encode",
        "decode",
        "serialize",
        "deserialize",
        "stringify",
        "clone",
        "merge",
        "deep",
        "flatten",
        "chunk",
        "debounce",
        "throttle",
        "memoize",
        "cache",
        "logger",
        "log",
        "error",
        "config",
        "constant",
        "enum",
    ],
}

# Ordered list of domains (matches feature vector order)
DOMAIN_ORDER = ["auth", "db", "api", "ui", "util"]


def extract_semantic_features(content: str) -> np.ndarray:
    """
    Extract semantic features from code content.

    Classifies code by domain based on keyword presence.
    Returns probability distribution across 5 domains.

    Args:
        content: Source code content as string.

    Returns:
        NumPy array of 5 features (sum approximately 1.0).
    """
    content_lower = content.lower()

    # Count keyword hits per domain
    domain_scores: dict[str, int] = {}

    for domain in DOMAIN_ORDER:
        keywords = DOMAIN_KEYWORDS[domain]
        score = 0

        for keyword in keywords:
            # Use word boundary to avoid partial matches
            pattern = r"\b" + re.escape(keyword) + r"\b"
            matches = len(re.findall(pattern, content_lower))
            score += matches

        domain_scores[domain] = score

    # Convert to probability distribution
    total = sum(domain_scores.values())

    if total == 0:
        # No keywords found, return uniform distribution
        return np.ones(SEMANTIC_DIMS, dtype=np.float64) / SEMANTIC_DIMS

    # Normalize to sum = 1.0
    features = np.array(
        [domain_scores[domain] / total for domain in DOMAIN_ORDER],
        dtype=np.float64,
    )

    return features


def get_domain_names() -> list[str]:
    """Return names of semantic domains in order."""
    return DOMAIN_ORDER.copy()


def get_dominant_domain(features: np.ndarray) -> str:
    """
    Get the dominant domain from semantic features.

    Args:
        features: Semantic feature vector (5 dimensions).

    Returns:
        Name of the domain with highest score.
    """
    idx = int(np.argmax(features))
    return DOMAIN_ORDER[idx]


def get_domain_distribution(features: np.ndarray) -> dict[str, float]:
    """
    Get domain distribution as dictionary.

    Args:
        features: Semantic feature vector (5 dimensions).

    Returns:
        Dictionary mapping domain names to scores.
    """
    return {domain: float(features[i]) for i, domain in enumerate(DOMAIN_ORDER)}

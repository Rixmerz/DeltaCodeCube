"""
Architectural pattern detection for code files.

Extracts 10D pattern features that identify common code patterns:
1. is_repository - CRUD methods
2. is_controller - request/response handlers
3. is_middleware - middleware pattern
4. is_factory - creates and returns instances
5. is_observer - event emitter pattern
6. is_config - constants/config exports
7. is_test - test file
8. is_types_only - only type definitions
9. is_entrypoint - main/entry point
10. is_migration - database migration

Uses tree-sitter queries when available, regex fallback otherwise.
"""

import re
from typing import Any

import numpy as np

PATTERN_DIMS = 10

# Pattern names in order
PATTERN_NAMES = [
    "is_repository",
    "is_controller",
    "is_middleware",
    "is_factory",
    "is_observer",
    "is_config",
    "is_test",
    "is_types_only",
    "is_entrypoint",
    "is_migration",
]

# Regex patterns for each architectural pattern
# Weights: domain-specific identifiers get high weight; generic verbs get low weight
# to avoid false positives on files that happen to use common words.
_PATTERN_REGEXES: dict[str, list[tuple[str, float]]] = {
    "is_repository": [
        (r"\b(?:find|get|fetch)(?:_?(?:all|by|one|many))\b", 0.3),
        (r"\b(?:save|create|insert|add)\b", 0.3),
        (r"\b(?:update|modify|patch)\b", 0.3),
        (r"\b(?:delete|remove|destroy)\b", 0.3),
        (r"(?:repository|repo|dao|store)\b", 3.0),
    ],
    "is_controller": [
        (r"\b(?:request|req)\b", 0.3),
        (r"\b(?:response|res)\b", 0.3),
        (r"\b(?:controller|handler|endpoint)\b", 2.0),
        (r"\b(?:get|post|put|patch|delete)\s*\(", 0.5),
        (r"@(?:app|router)\.\w+\(", 1.5),
        (r"@(?:Get|Post|Put|Delete|Patch)\(", 1.5),
    ],
    "is_middleware": [
        (r"\b(?:req|request)\b.*\b(?:res|response)\b.*\b(?:next|callback)\b", 3.0),
        (r"\bmiddleware\b", 2.0),
        (r"def\s+\w+\s*\(\s*(?:request|get_response)", 2.0),
        (r"@(?:middleware|before_request|after_request)\b", 2.0),
    ],
    "is_factory": [
        (r"\b(?:create|make|build|construct)\w*\s*\(", 0.3),
        (r"\breturn\s+(?:new\s+)?\w+\s*\(", 1.5),
        (r"\bfactory\b", 2.0),
        (r"\b(?:get_?instance|create_?instance)\b", 2.0),
    ],
    "is_observer": [
        (r"\b(?:on|emit|fire|trigger|dispatch)\s*\(", 0.3),
        (r"\b(?:subscribe|unsubscribe|listen|addEventListener)\b", 1.5),
        (r"\b(?:observer|listener|subscriber|emitter|event_?bus)\b", 2.0),
        (r"\b(?:EventEmitter|Subject|Observable)\b", 2.0),
    ],
    "is_config": [
        # Require const/let/var + UPPER_CASE name — excludes JSX attrs and function args
        (r"^\s*(?:export\s+)?(?:const|let|var)\s+[A-Z_]\w*\s*=\s*['\"\d{[]", 0.5),
        (r"\b(?:config|settings|options|defaults|constants)\b", 1.5),
        (r"(?:\.env|process\.env|os\.environ)\b", 1.5),
        # Python top-level UPPER_CASE assignments (config files)
        (r"^[A-Z_]{2,}\s*=\s*", 0.5),
    ],
    "is_test": [
        # Require string arg for describe/it — excludes .describe() (Zod, etc.)
        (r"(?<![.\w])(?:describe|it)\s*\(\s*['\"]", 1.5),
        # test() with string arg
        (r"(?<![.\w])test\s*\(\s*['\"]", 1.5),
        # expect/assert can have any arg (specific to testing)
        (r"\b(?:expect|assert)\s*\(", 1.0),
        (r"\bdef\s+test_\w+", 2.0),
        (r"\bclass\s+Test\w+", 2.0),
        (r"@pytest\.\w+|import\s+pytest\b", 2.0),
        (r"\.spec\.|\.test\.|_test\.py|test_\w+\.py", 2.0),
    ],
    "is_types_only": [
        (r"\b(?:interface|type)\s+\w+\s*[={]", 1.5),
        (r"\benum\s+\w+", 1.5),
        (r"\bclass\s+\w+\s*\(.*(?:TypedDict|NamedTuple|BaseModel)\)", 2.0),
        (r"\.d\.ts$", 3.0),
    ],
    "is_entrypoint": [
        (r"if\s+__name__\s*==\s*['\"]__main__['\"]", 3.0),
        (r"\b(?:app\.listen|app\.run|server\.start)\s*\(", 2.0),
        (r"\bmain\s*\(\s*\)", 2.0),
        (r"createApp\s*\(|ReactDOM\.render\s*\(", 2.0),
    ],
    # Python-only entrypoint patterns (filtered by extension at runtime)
    "_python_only_entrypoint": [
        (r"if\s+__name__\s*==\s*['\"]__main__['\"]", 3.0),
        (r"\bmain\s*\(\s*\)", 2.0),
    ],
    "is_migration": [
        (r"\bdef\s+(?:up|upgrade|forwards)\s*\(", 2.0),
        (r"\bdef\s+(?:down|downgrade|backwards)\s*\(", 2.0),
        (r"\b(?:ALTER|CREATE|DROP)\s+(?:TABLE|INDEX|COLUMN)\b", 2.0),
        (r"\bmigration\b", 1.5),
        (r"\b(?:add_column|remove_column|create_table|drop_table)\b", 2.0),
    ],
}

# Thresholds: how many weighted matches indicate this pattern
_PATTERN_THRESHOLDS: dict[str, float] = {
    "is_repository": 6.0,
    "is_controller": 6.0,
    "is_middleware": 3.0,
    "is_factory": 5.0,
    "is_observer": 5.0,
    "is_config": 5.0,
    "is_test": 3.0,
    "is_types_only": 3.0,
    "is_entrypoint": 3.0,
    "is_migration": 4.0,
}


def extract_pattern_features(content: str, extension: str = ".py") -> np.ndarray:
    """
    Extract 10D architectural pattern features from code content.

    Each dimension is a score from 0.0 to 1.0 indicating how strongly
    the code matches the pattern.

    Args:
        content: Source code content as string.
        extension: File extension for language detection.

    Returns:
        NumPy array of 10 pattern scores.
    """
    features = np.zeros(PATTERN_DIMS, dtype=np.float64)
    is_python = extension in ('.py', '.pyw')

    for i, pattern_name in enumerate(PATTERN_NAMES):
        regexes = _PATTERN_REGEXES.get(pattern_name, [])
        threshold = _PATTERN_THRESHOLDS.get(pattern_name, 3.0)

        # Fix 2: is_types_only uses ratio-based scoring
        if pattern_name == "is_types_only":
            type_decls = 0
            for regex, weight in regexes:
                try:
                    type_decls += len(re.findall(regex, content, re.MULTILINE | re.IGNORECASE))
                except re.error:
                    continue
            total_lines = max(content.count("\n") + 1, 1)
            ratio = type_decls / total_lines
            # Only score high if >20% of file is type declarations
            features[i] = min(1.0, ratio * 5)  # 20% -> 1.0, 10% -> 0.5, 4% -> 0.2
            continue

        # Fix 4: Filter Python-only patterns from is_entrypoint for non-Python files
        if pattern_name == "is_entrypoint" and not is_python:
            python_only = _PATTERN_REGEXES.get("_python_only_entrypoint", [])
            python_only_patterns = {r for r, _ in python_only}
            regexes = [(r, w) for r, w in regexes if r not in python_only_patterns]

        score = 0.0
        for regex, weight in regexes:
            try:
                matches = len(re.findall(regex, content, re.MULTILINE | re.IGNORECASE))
                score += min(matches, 5) * weight  # cap per-regex at 5 hits
            except re.error:
                continue

        features[i] = min(1.0, score / threshold)

    # Dampen non-dominant patterns: keep top 2 unchanged, reduce the rest
    sorted_indices = np.argsort(features)[::-1]
    for rank, idx in enumerate(sorted_indices):
        if rank >= 2 and features[idx] > 0:
            features[idx] *= 0.3

    return features

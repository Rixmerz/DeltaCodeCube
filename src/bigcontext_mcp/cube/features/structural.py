"""
Structural feature extractor for code files.

Extracts 8 structural features using regex/heuristics (no AST required):
1. loc_normalized: Lines of code (normalized to 500)
2. num_functions: Number of function definitions
3. num_classes: Number of class definitions
4. num_imports: Number of import statements
5. avg_indent: Average indentation depth
6. comment_ratio: Ratio of comment lines
7. cyclomatic_estimate: Estimated cyclomatic complexity
8. export_count: Number of exports
"""

import re
from typing import Any

import numpy as np

# Feature dimension
STRUCTURAL_DIMS = 8


def extract_structural_features(content: str, extension: str = ".js") -> np.ndarray:
    """
    Extract structural features from code content.

    Args:
        content: Source code content as string.
        extension: File extension for language-specific patterns.

    Returns:
        NumPy array of 8 normalized features.
    """
    lines = content.split("\n")
    non_empty_lines = [line for line in lines if line.strip()]

    features = {
        "loc_normalized": _extract_loc(lines),
        "num_functions": _extract_function_count(content, extension),
        "num_classes": _extract_class_count(content),
        "num_imports": _extract_import_count(content, extension),
        "avg_indent": _extract_avg_indent(non_empty_lines),
        "comment_ratio": _extract_comment_ratio(content, lines),
        "cyclomatic_estimate": _extract_cyclomatic(content, lines),
        "export_count": _extract_export_count(content, extension),
    }

    return np.array(list(features.values()), dtype=np.float64)


def _extract_loc(lines: list[str]) -> float:
    """Lines of code normalized to 500."""
    return min(len(lines) / 500.0, 1.0)


def _extract_function_count(content: str, extension: str) -> float:
    """Count function definitions, normalized to 20."""
    patterns = [
        r"\bfunction\s+\w+\s*\(",  # function name()
        r"\bfunction\s*\(",  # function()
        r"(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?\(",  # const fn = () or const fn = async (
        r"(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?function",  # const fn = function
        r"\bdef\s+\w+\s*\(",  # Python def
        r"\basync\s+def\s+\w+\s*\(",  # Python async def
        r"=>\s*{",  # Arrow functions with body
    ]

    count = 0
    for pattern in patterns:
        count += len(re.findall(pattern, content))

    return min(count / 20.0, 1.0)


def _extract_class_count(content: str) -> float:
    """Count class definitions, normalized to 10."""
    count = len(re.findall(r"\bclass\s+\w+", content))
    return min(count / 10.0, 1.0)


def _extract_import_count(content: str, extension: str) -> float:
    """Count import statements, normalized to 30."""
    patterns = [
        r"\bimport\s+",  # ES6 import / Python import
        r"\brequire\s*\(",  # CommonJS require
        r"\bfrom\s+['\"]",  # ES6 from 'x'
        r"\bfrom\s+\w+\s+import",  # Python from x import
    ]

    count = 0
    for pattern in patterns:
        count += len(re.findall(pattern, content))

    return min(count / 30.0, 1.0)


def _extract_avg_indent(non_empty_lines: list[str]) -> float:
    """Average indentation depth, normalized to 4 tabs."""
    if not non_empty_lines:
        return 0.0

    total_indent = 0
    for line in non_empty_lines:
        # Count leading whitespace
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        # Normalize to tabs (assuming 2 or 4 spaces = 1 tab)
        total_indent += indent / 4.0

    avg = total_indent / len(non_empty_lines)
    return min(avg / 4.0, 1.0)  # Normalize to max 4 levels


def _extract_comment_ratio(content: str, lines: list[str]) -> float:
    """Ratio of comment content to total content."""
    if not lines:
        return 0.0

    comment_patterns = [
        r"//.*$",  # Single line JS/C++
        r"#.*$",  # Python/Shell
        r"/\*[\s\S]*?\*/",  # Multi-line JS/C
        r'"""[\s\S]*?"""',  # Python docstring
        r"'''[\s\S]*?'''",  # Python docstring
    ]

    comment_chars = 0
    for pattern in comment_patterns:
        for match in re.finditer(pattern, content, re.MULTILINE):
            comment_chars += len(match.group())

    total_chars = len(content) or 1
    return min(comment_chars / total_chars, 1.0)


def _extract_cyclomatic(content: str, lines: list[str]) -> float:
    """
    Estimate cyclomatic complexity.

    Counts decision points: if, else, elif, for, while, switch, case, catch, &&, ||, ?:
    """
    if not lines:
        return 0.0

    patterns = [
        r"\bif\b",
        r"\belse\b",
        r"\belif\b",
        r"\bfor\b",
        r"\bwhile\b",
        r"\bswitch\b",
        r"\bcase\b",
        r"\bcatch\b",
        r"\btry\b",
        r"&&",
        r"\|\|",
        r"\?.*:",  # Ternary
    ]

    count = 0
    for pattern in patterns:
        count += len(re.findall(pattern, content))

    # Normalize: assume 100 decision points in 500 lines is high complexity
    loc = len(lines) or 1
    complexity_per_line = count / loc
    return min(complexity_per_line * 5, 1.0)


def _extract_export_count(content: str, extension: str) -> float:
    """Count exports, normalized to 15."""
    patterns = [
        r"\bexport\s+",  # ES6 export
        r"\bexports\.",  # CommonJS exports.x
        r"\bmodule\.exports",  # CommonJS module.exports
        r"__all__\s*=",  # Python __all__
    ]

    count = 0
    for pattern in patterns:
        count += len(re.findall(pattern, content))

    return min(count / 15.0, 1.0)


def get_feature_names() -> list[str]:
    """Return names of structural features in order."""
    return [
        "loc_normalized",
        "num_functions",
        "num_classes",
        "num_imports",
        "avg_indent",
        "comment_ratio",
        "cyclomatic_estimate",
        "export_count",
    ]

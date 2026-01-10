"""
DeltaCodeCube - Sistema de indexación multidimensional para código.

Representa código como puntos en espacio 3D (Lexical, Structural, Semantic)
para búsqueda multidimensional y detección de impacto de cambios.
"""

from deltacodecube.cube.code_point import CodePoint
from deltacodecube.cube.contracts import Contract, ContractDetector
from deltacodecube.cube.cube import DeltaCodeCube
from deltacodecube.cube.delta import Delta, DeltaTracker, create_delta
from deltacodecube.cube.tension import Tension, TensionDetector
from deltacodecube.cube.suggestions import (
    ChangeAnalysis,
    SuggestionGenerator,
    analyze_change_type,
    extract_relevant_snippets,
)

__all__ = [
    "ChangeAnalysis",
    "CodePoint",
    "Contract",
    "ContractDetector",
    "Delta",
    "DeltaCodeCube",
    "DeltaTracker",
    "SuggestionGenerator",
    "Tension",
    "TensionDetector",
    "analyze_change_type",
    "create_delta",
    "extract_relevant_snippets",
]

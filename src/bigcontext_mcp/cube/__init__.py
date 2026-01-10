"""
DeltaCodeCube - Sistema de indexación multidimensional para código.

Representa código como puntos en espacio 3D (Lexical, Structural, Semantic)
para búsqueda multidimensional y detección de impacto de cambios.
"""

from bigcontext_mcp.cube.code_point import CodePoint
from bigcontext_mcp.cube.contracts import Contract, ContractDetector
from bigcontext_mcp.cube.cube import DeltaCodeCube
from bigcontext_mcp.cube.delta import Delta, DeltaTracker, create_delta
from bigcontext_mcp.cube.tension import Tension, TensionDetector

__all__ = [
    "CodePoint",
    "Contract",
    "ContractDetector",
    "Delta",
    "DeltaCodeCube",
    "DeltaTracker",
    "Tension",
    "TensionDetector",
    "create_delta",
]

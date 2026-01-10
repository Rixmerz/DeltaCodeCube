"""
CodePoint - Representation of code as a point in 3D feature space.

A CodePoint represents a code file (or function) as a vector in 63-dimensional space:
- Lexical features (50 dims): TF-IDF based term importance
- Structural features (8 dims): Code structure metrics
- Semantic features (5 dims): Domain classification
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from deltacodecube.cube.features import (
    extract_lexical_features,
    extract_semantic_features,
    extract_structural_features,
)
from deltacodecube.cube.features.lexical import LEXICAL_DIMS
from deltacodecube.cube.features.semantic import SEMANTIC_DIMS, get_dominant_domain
from deltacodecube.cube.features.structural import STRUCTURAL_DIMS

# Total dimensions
TOTAL_DIMS = LEXICAL_DIMS + STRUCTURAL_DIMS + SEMANTIC_DIMS  # 50 + 8 + 5 = 63


@dataclass
class CodePoint:
    """
    Represents a code file as a point in 3D feature space.

    The position vector is 63 dimensions:
    - [0:50] Lexical features
    - [50:58] Structural features
    - [58:63] Semantic features
    """

    # Identification
    id: str
    file_path: str
    function_name: str | None = None

    # Feature vectors
    lexical: np.ndarray = field(default_factory=lambda: np.zeros(LEXICAL_DIMS))
    structural: np.ndarray = field(default_factory=lambda: np.zeros(STRUCTURAL_DIMS))
    semantic: np.ndarray = field(default_factory=lambda: np.zeros(SEMANTIC_DIMS))

    # Metadata
    content_hash: str = ""
    line_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def position(self) -> np.ndarray:
        """
        Full position vector in 63-dimensional space.

        Returns:
            Concatenated feature vector [lexical, structural, semantic].
        """
        return np.concatenate([self.lexical, self.structural, self.semantic])

    @property
    def dominant_domain(self) -> str:
        """Get the dominant semantic domain."""
        return get_dominant_domain(self.semantic)

    def distance_to(self, other: "CodePoint") -> float:
        """
        Calculate Euclidean distance to another CodePoint.

        Args:
            other: Another CodePoint.

        Returns:
            Euclidean distance between positions.
        """
        return float(np.linalg.norm(self.position - other.position))

    def distance_in_axis(self, other: "CodePoint", axis: str) -> float:
        """
        Calculate distance in a specific axis/dimension.

        Args:
            other: Another CodePoint.
            axis: One of 'lexical', 'structural', 'semantic'.

        Returns:
            Euclidean distance in specified dimensions only.
        """
        if axis == "lexical":
            return float(np.linalg.norm(self.lexical - other.lexical))
        elif axis == "structural":
            return float(np.linalg.norm(self.structural - other.structural))
        elif axis == "semantic":
            return float(np.linalg.norm(self.semantic - other.semantic))
        else:
            raise ValueError(f"Unknown axis: {axis}. Use 'lexical', 'structural', or 'semantic'.")

    def similarity_to(self, other: "CodePoint") -> float:
        """
        Calculate cosine similarity to another CodePoint.

        Args:
            other: Another CodePoint.

        Returns:
            Cosine similarity (0 to 1, higher is more similar).
        """
        pos1 = self.position
        pos2 = other.position
        norm1 = np.linalg.norm(pos1)
        norm2 = np.linalg.norm(pos2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(pos1, pos2) / (norm1 * norm2))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "file_path": self.file_path,
            "function_name": self.function_name,
            "lexical": self.lexical.tolist(),
            "structural": self.structural.tolist(),
            "semantic": self.semantic.tolist(),
            "content_hash": self.content_hash,
            "line_count": self.line_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CodePoint":
        """Create CodePoint from dictionary."""
        return cls(
            id=data["id"],
            file_path=data["file_path"],
            function_name=data.get("function_name"),
            lexical=np.array(data["lexical"], dtype=np.float64),
            structural=np.array(data["structural"], dtype=np.float64),
            semantic=np.array(data["semantic"], dtype=np.float64),
            content_hash=data.get("content_hash", ""),
            line_count=data.get("line_count", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )

    def __repr__(self) -> str:
        return (
            f"CodePoint(id='{self.id}', "
            f"file='{Path(self.file_path).name}', "
            f"domain='{self.dominant_domain}')"
        )


def create_code_point(
    file_path: str,
    content: str | None = None,
    function_name: str | None = None,
) -> CodePoint:
    """
    Create a CodePoint from a file path or content.

    Args:
        file_path: Path to the code file.
        content: Optional content (reads from file if not provided).
        function_name: Optional function name if indexing a specific function.

    Returns:
        CodePoint with extracted features.
    """
    path = Path(file_path)

    # Read content if not provided
    if content is None:
        content = path.read_text(encoding="utf-8")

    # Generate ID
    point_id = _generate_id(file_path, function_name)

    # Calculate hash
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    # Get file extension
    extension = path.suffix

    # Extract features
    lexical = extract_lexical_features(content)
    structural = extract_structural_features(content, extension)
    semantic = extract_semantic_features(content)

    # Count lines
    line_count = content.count("\n") + 1

    return CodePoint(
        id=point_id,
        file_path=str(path.absolute()),
        function_name=function_name,
        lexical=lexical,
        structural=structural,
        semantic=semantic,
        content_hash=content_hash,
        line_count=line_count,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def _generate_id(file_path: str, function_name: str | None = None) -> str:
    """Generate unique ID for a CodePoint."""
    base = file_path
    if function_name:
        base = f"{file_path}::{function_name}"

    # Create short hash
    return hashlib.md5(base.encode("utf-8")).hexdigest()[:12]

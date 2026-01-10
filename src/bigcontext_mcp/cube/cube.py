"""
DeltaCodeCube - Main class for 3D code indexing system.

Manages CodePoints in a 63-dimensional feature space and provides:
- Indexing of code files
- Similarity search
- Position queries
- Persistence to SQLite
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from bigcontext_mcp.cube.code_point import CodePoint, create_code_point
from bigcontext_mcp.cube.features.semantic import get_dominant_domain
from bigcontext_mcp.utils.logger import get_logger

logger = get_logger(__name__)


class DeltaCodeCube:
    """
    3D code indexing system based on feature space representation.

    Each code file is represented as a point in 63-dimensional space:
    - Lexical (50 dims): Term importance via TF
    - Structural (8 dims): Code structure metrics
    - Semantic (5 dims): Domain classification

    Supports:
    - Indexing individual files or directories
    - Similarity search (find similar files)
    - Position queries (get file's position in cube)
    - Persistence to SQLite database
    """

    def __init__(self, conn: sqlite3.Connection):
        """
        Initialize DeltaCodeCube with database connection.

        Args:
            conn: SQLite connection (should have dict_factory row_factory).
        """
        self.conn = conn
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        """Ensure cube tables exist in database."""
        # Tables are created by main schema, but verify
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='code_points'"
        )
        if not cursor.fetchone():
            logger.warning("code_points table not found - cube features may not work")

    def index_file(self, file_path: str, content: str | None = None) -> CodePoint:
        """
        Index a single code file.

        Args:
            file_path: Path to the code file.
            content: Optional content (reads from file if not provided).

        Returns:
            Created or updated CodePoint.
        """
        path = Path(file_path).resolve()

        # Read content if not provided
        if content is None:
            content = path.read_text(encoding="utf-8")

        # Create CodePoint
        code_point = create_code_point(str(path), content)

        # Check if exists
        existing = self._get_code_point_by_path(str(path))

        if existing:
            # Update existing
            code_point.created_at = existing.created_at
            self._update_code_point(code_point)
            logger.info(f"Updated code point: {path.name}")
        else:
            # Insert new
            self._insert_code_point(code_point)
            logger.info(f"Indexed code point: {path.name}")

        return code_point

    def index_directory(
        self,
        directory: str,
        patterns: list[str] | None = None,
        recursive: bool = True,
    ) -> list[CodePoint]:
        """
        Index all code files in a directory.

        Args:
            directory: Path to directory.
            patterns: Glob patterns for files (default: common code extensions).
            recursive: Whether to search recursively.

        Returns:
            List of created CodePoints.
        """
        dir_path = Path(directory).resolve()

        if patterns is None:
            patterns = ["*.js", "*.jsx", "*.ts", "*.tsx", "*.py", "*.go", "*.java"]

        code_points = []

        for pattern in patterns:
            if recursive:
                files = dir_path.rglob(pattern)
            else:
                files = dir_path.glob(pattern)

            for file_path in files:
                # Skip node_modules, .git, etc.
                if self._should_skip(file_path):
                    continue

                try:
                    cp = self.index_file(str(file_path))
                    code_points.append(cp)
                except Exception as e:
                    logger.warning(f"Failed to index {file_path}: {e}")

        logger.info(f"Indexed {len(code_points)} files from {dir_path}")
        return code_points

    def _should_skip(self, file_path: Path) -> bool:
        """Check if file should be skipped during indexing."""
        skip_dirs = {
            "node_modules",
            ".git",
            ".next",
            "__pycache__",
            ".venv",
            "venv",
            "dist",
            "build",
            ".cache",
            "coverage",
        }

        for part in file_path.parts:
            if part in skip_dirs:
                return True

        return False

    def get_code_point(self, file_path: str) -> CodePoint | None:
        """
        Get CodePoint for a file.

        Args:
            file_path: Path to the code file.

        Returns:
            CodePoint if found, None otherwise.
        """
        path = Path(file_path).resolve()
        return self._get_code_point_by_path(str(path))

    def get_position(self, file_path: str) -> dict[str, Any] | None:
        """
        Get position of a file in the cube.

        Args:
            file_path: Path to the code file.

        Returns:
            Dictionary with position info, or None if not indexed.
        """
        code_point = self.get_code_point(file_path)

        if not code_point:
            return None

        return {
            "file_path": code_point.file_path,
            "id": code_point.id,
            "position": {
                "lexical": code_point.lexical.tolist(),
                "structural": code_point.structural.tolist(),
                "semantic": code_point.semantic.tolist(),
                "full": code_point.position.tolist(),
            },
            "dominant_domain": code_point.dominant_domain,
            "line_count": code_point.line_count,
            "content_hash": code_point.content_hash,
        }

    def find_similar(
        self,
        file_path: str,
        limit: int = 5,
        axis: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Find files similar to a given file.

        Args:
            file_path: Path to reference file.
            limit: Maximum results to return.
            axis: Specific axis to compare ('lexical', 'structural', 'semantic', or None for all).

        Returns:
            List of similar files with distances.
        """
        reference = self.get_code_point(file_path)

        if not reference:
            return []

        # Get all code points
        all_points = self._get_all_code_points()

        # Calculate distances
        results = []
        for cp in all_points:
            if cp.id == reference.id:
                continue

            if axis:
                distance = reference.distance_in_axis(cp, axis)
            else:
                distance = reference.distance_to(cp)

            results.append({
                "file_path": cp.file_path,
                "id": cp.id,
                "distance": distance,
                "similarity": reference.similarity_to(cp),
                "dominant_domain": cp.dominant_domain,
            })

        # Sort by distance (ascending)
        results.sort(key=lambda x: x["distance"])

        return results[:limit]

    def search_by_domain(self, domain: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Find files by semantic domain.

        Args:
            domain: Domain name ('auth', 'db', 'api', 'ui', 'util').
            limit: Maximum results.

        Returns:
            List of files in the specified domain.
        """
        cursor = self.conn.execute(
            """
            SELECT * FROM code_points
            WHERE dominant_domain = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (domain, limit),
        )

        results = []
        for row in cursor.fetchall():
            results.append({
                "file_path": row["file_path"],
                "id": row["id"],
                "dominant_domain": row["dominant_domain"],
                "line_count": row["line_count"],
            })

        return results

    def get_stats(self) -> dict[str, Any]:
        """
        Get statistics about indexed code.

        Returns:
            Dictionary with cube statistics.
        """
        # Total code points
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM code_points")
        total = cursor.fetchone()["count"]

        # By domain
        cursor = self.conn.execute(
            """
            SELECT dominant_domain, COUNT(*) as count
            FROM code_points
            GROUP BY dominant_domain
            """
        )
        by_domain = {row["dominant_domain"]: row["count"] for row in cursor.fetchall()}

        # Total lines
        cursor = self.conn.execute("SELECT SUM(line_count) as total FROM code_points")
        result = cursor.fetchone()
        total_lines = result["total"] or 0

        return {
            "total_files": total,
            "total_lines": total_lines,
            "by_domain": by_domain,
        }

    def list_code_points(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """
        List all indexed code points.

        Args:
            limit: Maximum results.
            offset: Offset for pagination.

        Returns:
            List of code point summaries.
        """
        cursor = self.conn.execute(
            """
            SELECT id, file_path, function_name, dominant_domain, line_count, created_at
            FROM code_points
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )

        return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # Database operations
    # =========================================================================

    def _insert_code_point(self, cp: CodePoint) -> None:
        """Insert a new CodePoint into database."""
        self.conn.execute(
            """
            INSERT INTO code_points (
                id, file_path, function_name,
                lexical_features, structural_features, semantic_features,
                content_hash, line_count, dominant_domain,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cp.id,
                cp.file_path,
                cp.function_name,
                json.dumps(cp.lexical.tolist()),
                json.dumps(cp.structural.tolist()),
                json.dumps(cp.semantic.tolist()),
                cp.content_hash,
                cp.line_count,
                cp.dominant_domain,
                cp.created_at.isoformat(),
                cp.updated_at.isoformat(),
            ),
        )
        self.conn.commit()

    def _update_code_point(self, cp: CodePoint) -> None:
        """Update an existing CodePoint in database."""
        self.conn.execute(
            """
            UPDATE code_points SET
                lexical_features = ?,
                structural_features = ?,
                semantic_features = ?,
                content_hash = ?,
                line_count = ?,
                dominant_domain = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                json.dumps(cp.lexical.tolist()),
                json.dumps(cp.structural.tolist()),
                json.dumps(cp.semantic.tolist()),
                cp.content_hash,
                cp.line_count,
                cp.dominant_domain,
                cp.updated_at.isoformat(),
                cp.id,
            ),
        )
        self.conn.commit()

    def _get_code_point_by_path(self, file_path: str) -> CodePoint | None:
        """Get CodePoint by file path."""
        cursor = self.conn.execute(
            "SELECT * FROM code_points WHERE file_path = ?",
            (file_path,),
        )
        row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_code_point(row)

    def _get_all_code_points(self) -> list[CodePoint]:
        """Get all CodePoints from database."""
        cursor = self.conn.execute("SELECT * FROM code_points")
        return [self._row_to_code_point(row) for row in cursor.fetchall()]

    def _row_to_code_point(self, row: dict[str, Any]) -> CodePoint:
        """Convert database row to CodePoint."""
        return CodePoint(
            id=row["id"],
            file_path=row["file_path"],
            function_name=row.get("function_name"),
            lexical=np.array(json.loads(row["lexical_features"]), dtype=np.float64),
            structural=np.array(json.loads(row["structural_features"]), dtype=np.float64),
            semantic=np.array(json.loads(row["semantic_features"]), dtype=np.float64),
            content_hash=row["content_hash"],
            line_count=row["line_count"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

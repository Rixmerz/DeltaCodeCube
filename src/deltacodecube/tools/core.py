"""Core indexing tools for DeltaCodeCube."""

from typing import Any

from deltacodecube.db.database import get_connection
from deltacodecube.cube import DeltaCodeCube


def register_core_tools(mcp):
    """Register core indexing tools with MCP server."""

    @mcp.tool()
    def cube_index_file(path: str) -> dict[str, Any]:
        """
        Index a code file into the DeltaCodeCube.

        Extracts lexical, structural, and semantic features and stores
        the file as a point in 63-dimensional feature space.

        Args:
            path: Absolute path to the code file.

        Returns:
            CodePoint information including position in cube.
        """
        with get_connection() as conn:
            cube = DeltaCodeCube(conn)
            code_point = cube.index_file(path)
            return code_point.to_dict()

    @mcp.tool()
    def cube_index_directory(
        path: str,
        patterns: list[str] | None = None,
        recursive: bool = True,
    ) -> dict[str, Any]:
        """
        Index all code files in a directory.

        Args:
            path: Absolute path to directory.
            patterns: Glob patterns for files (default: js, ts, py, go, java).
            recursive: Whether to search recursively (default: True).

        Returns:
            Summary of indexed files.
        """
        with get_connection() as conn:
            cube = DeltaCodeCube(conn)
            code_points = cube.index_directory(path, patterns, recursive)

            return {
                "indexed_count": len(code_points),
                "files": [
                    {
                        "path": cp.file_path,
                        "domain": cp.dominant_domain,
                        "lines": cp.line_count,
                    }
                    for cp in code_points
                ],
            }

    @mcp.tool()
    def cube_get_position(path: str) -> dict[str, Any]:
        """
        Get the position of a code file in the DeltaCodeCube.

        Returns the file's coordinates in the 63-dimensional feature space,
        broken down by lexical, structural, and semantic components.

        Args:
            path: Absolute path to the code file.

        Returns:
            Position information including feature vectors and dominant domain.
        """
        with get_connection() as conn:
            cube = DeltaCodeCube(conn)
            position = cube.get_position(path)

            if not position:
                return {"error": f"File not indexed: {path}"}

            return position

    @mcp.tool()
    def cube_find_similar(
        path: str,
        limit: int = 5,
        axis: str | None = None,
    ) -> dict[str, Any]:
        """
        Find code files similar to a given file.

        Searches for files with closest positions in the feature space.
        Can optionally search in a specific axis only.

        Args:
            path: Absolute path to reference file.
            limit: Maximum results to return (default: 5).
            axis: Specific axis to compare ('lexical', 'structural', 'semantic', or None for all).

        Returns:
            List of similar files with distances and similarity scores.
        """
        with get_connection() as conn:
            cube = DeltaCodeCube(conn)
            results = cube.find_similar(path, limit, axis)

            if not results:
                return {"error": f"File not indexed or no similar files found: {path}"}

            return {"similar_files": results}

    @mcp.tool()
    def cube_search_by_domain(domain: str, limit: int = 10) -> dict[str, Any]:
        """
        Find code files by semantic domain.

        Searches for files classified in a specific functional domain.

        Args:
            domain: Domain name ('auth', 'db', 'api', 'ui', 'util').
            limit: Maximum results (default: 10).

        Returns:
            List of files in the specified domain.
        """
        with get_connection() as conn:
            cube = DeltaCodeCube(conn)
            results = cube.search_by_domain(domain, limit)
            return {"files": results, "domain": domain, "count": len(results)}

    @mcp.tool()
    def cube_get_stats() -> dict[str, Any]:
        """
        Get statistics about the DeltaCodeCube.

        Returns counts of indexed files, lines of code, and distribution by domain.

        Returns:
            Cube statistics.
        """
        with get_connection() as conn:
            cube = DeltaCodeCube(conn)
            return cube.get_stats()

    @mcp.tool()
    def cube_list_code_points(limit: int = 100, offset: int = 0) -> dict[str, Any]:
        """
        List all indexed code points.

        Args:
            limit: Maximum results (default: 100).
            offset: Offset for pagination (default: 0).

        Returns:
            List of code point summaries.
        """
        with get_connection() as conn:
            cube = DeltaCodeCube(conn)
            code_points = cube.list_code_points(limit, offset)
            return {"code_points": code_points, "count": len(code_points)}

"""FastMCP server for DeltaCodeCube.

Multi-dimensional code indexing - represent code as points in 63D feature space
for similarity search, impact analysis, and change detection.
"""

from typing import Any

from fastmcp import FastMCP

from deltacodecube.db.database import get_connection
from deltacodecube.cube import DeltaCodeCube

# Create FastMCP server
mcp = FastMCP("deltacodecube")


# =============================================================================
# Core Indexing Tools
# =============================================================================


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


# =============================================================================
# Contract Tools
# =============================================================================


@mcp.tool()
def cube_get_contracts(
    path: str | None = None,
    direction: str = "both",
    limit: int = 100,
) -> dict[str, Any]:
    """
    Get contracts (dependencies) between code files.

    A contract represents an import/require relationship between two files.
    Each contract includes a baseline_distance that represents the "healthy"
    distance between caller and callee in the 63D feature space.

    Args:
        path: Optional file path to filter contracts for a specific file.
        direction: Filter direction when path is provided:
                  - 'incoming': Files that import this file (dependents)
                  - 'outgoing': Files this file imports (dependencies)
                  - 'both': All contracts involving this file (default)
        limit: Maximum contracts to return (default: 100).

    Returns:
        Contract list with caller/callee info and baseline distances.
    """
    with get_connection() as conn:
        cube = DeltaCodeCube(conn)
        contracts = cube.get_contracts(file_path=path, direction=direction, limit=limit)
        return {"contracts": contracts, "count": len(contracts)}


@mcp.tool()
def cube_get_contract_stats() -> dict[str, Any]:
    """
    Get statistics about detected contracts.

    Returns total contracts, breakdown by type, and distance statistics.

    Returns:
        Contract statistics.
    """
    with get_connection() as conn:
        cube = DeltaCodeCube(conn)
        return cube.get_contract_stats()


# =============================================================================
# Delta and Tension Tools
# =============================================================================


@mcp.tool()
def cube_reindex(path: str) -> dict[str, Any]:
    """
    Re-index a file and detect changes (deltas) and tensions.

    When a code file changes, this tool:
    1. Compares the new code with the previously indexed version
    2. Creates a Delta recording the movement in 63D feature space
    3. Detects any Tensions (contracts that may be broken)
    4. Updates the CodePoint in the database

    Use this after modifying a file to see what impact the changes have.

    Args:
        path: Absolute path to the file that changed.

    Returns:
        Reindex result with delta and detected tensions.
    """
    with get_connection() as conn:
        cube = DeltaCodeCube(conn)
        return cube.reindex_file(path)


@mcp.tool()
def cube_analyze_impact(path: str) -> dict[str, Any]:
    """
    Analyze potential impact if a file were to change.

    Shows all files that depend on this file (import it) and their
    current distances in the 63D feature space. Useful for:
    - Understanding dependencies before making changes
    - Identifying high-impact files
    - Planning refactoring

    Args:
        path: Absolute path to the file to analyze.

    Returns:
        Impact analysis with list of dependent files and their distances.
    """
    with get_connection() as conn:
        cube = DeltaCodeCube(conn)
        return cube.analyze_impact(path)


@mcp.tool()
def cube_get_tensions(
    status: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """
    Get detected tensions (potential contract violations).

    A Tension is created when a code file changes and its distance to
    dependent files deviates significantly from the baseline. This indicates
    the change may have broken implicit dependencies.

    Args:
        status: Filter by status:
               - 'detected': New tensions not yet reviewed
               - 'reviewed': Tensions that have been seen
               - 'resolved': Fixed tensions
               - 'ignored': Tensions marked as non-issues
               - None: All tensions (default)
        limit: Maximum tensions to return (default: 50).

    Returns:
        List of tensions with severity and suggested actions.
    """
    with get_connection() as conn:
        cube = DeltaCodeCube(conn)
        tensions = cube.get_tensions(status=status, limit=limit)
        stats = cube.get_tension_stats()
        return {
            "tensions": tensions,
            "count": len(tensions),
            "stats": stats,
        }


@mcp.tool()
def cube_resolve_tension(tension_id: str, status: str = "resolved") -> dict[str, Any]:
    """
    Update the status of a tension.

    After reviewing a tension, mark it as resolved, ignored, or reviewed.

    Args:
        tension_id: ID of the tension to update.
        status: New status:
               - 'reviewed': Marked as seen but not yet fixed
               - 'resolved': Fixed and no longer an issue
               - 'ignored': Not a real issue, ignore it

    Returns:
        Update result.
    """
    with get_connection() as conn:
        cube = DeltaCodeCube(conn)
        success = cube.resolve_tension(tension_id, status)
        return {
            "success": success,
            "tension_id": tension_id,
            "new_status": status if success else None,
            "message": "Tension updated." if success else "Tension not found.",
        }


@mcp.tool()
def cube_get_deltas(limit: int = 20) -> dict[str, Any]:
    """
    Get recent code changes (deltas).

    Shows history of code movements in the 63D feature space.
    Each delta records what changed (lexical, structural, semantic)
    and by how much.

    Args:
        limit: Maximum deltas to return (default: 20).

    Returns:
        List of recent deltas with movement analysis.
    """
    with get_connection() as conn:
        cube = DeltaCodeCube(conn)
        deltas = cube.get_deltas(limit=limit)
        return {
            "deltas": deltas,
            "count": len(deltas),
        }


# =============================================================================
# Advanced Search Tools
# =============================================================================


@mcp.tool()
def cube_compare(path_a: str, path_b: str) -> dict[str, Any]:
    """
    Compare two code files in the DeltaCodeCube.

    Shows detailed comparison including:
    - Distance in each axis (lexical, structural, semantic)
    - Overall similarity score
    - Insights about what makes them similar/different

    Useful for:
    - Understanding code relationships
    - Finding refactoring opportunities
    - Comparing implementations

    Args:
        path_a: Absolute path to first file.
        path_b: Absolute path to second file.

    Returns:
        Detailed comparison with distances, similarity, and insights.
    """
    with get_connection() as conn:
        cube = DeltaCodeCube(conn)
        return cube.compare_files(path_a, path_b)


@mcp.tool()
def cube_export_positions(
    format: str = "3d",
    include_features: bool = False,
) -> dict[str, Any]:
    """
    Export code point positions for external visualization.

    Exports all indexed files with their positions in the 63D feature space.
    Supports multiple formats for different visualization tools.

    Args:
        format: Export format:
               - '3d': Simplified 3D coordinates (x=lexical, y=structural, z=semantic)
               - 'json': Full JSON with optional feature vectors
               - 'csv': CSV-ready format with headers
        include_features: Include full 63D feature vectors (only for 'json' format).

    Returns:
        Export data with positions and metadata.
    """
    with get_connection() as conn:
        cube = DeltaCodeCube(conn)
        return cube.export_positions(format=format, include_features=include_features)


@mcp.tool()
def cube_find_by_criteria(
    domain: str | None = None,
    min_lines: int | None = None,
    max_lines: int | None = None,
    similar_to: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """
    Find files matching multiple criteria.

    Combines domain filtering, size filtering, and similarity search
    in a single query. More flexible than individual search tools.

    Args:
        domain: Filter by domain ('auth', 'db', 'api', 'ui', 'util').
        min_lines: Minimum line count filter.
        max_lines: Maximum line count filter.
        similar_to: Path to file to find similar files to.
        limit: Maximum results (default: 20).

    Returns:
        List of matching files with optional similarity scores.

    Examples:
        - Find large DB files: domain="db", min_lines=200
        - Find small API files similar to X: domain="api", max_lines=100, similar_to="/path/to/x.js"
    """
    with get_connection() as conn:
        cube = DeltaCodeCube(conn)
        results = cube.find_by_criteria(
            domain=domain,
            min_lines=min_lines,
            max_lines=max_lines,
            similar_to=similar_to,
            limit=limit,
        )
        return {
            "files": results,
            "count": len(results),
            "filters": {
                "domain": domain,
                "min_lines": min_lines,
                "max_lines": max_lines,
                "similar_to": similar_to,
            },
        }


# =============================================================================
# Suggestion Tools
# =============================================================================


@mcp.tool()
def cube_suggest_fix(
    tension_id: str | None = None,
    file_path: str | None = None,
) -> dict[str, Any]:
    """
    Generate fix suggestion context for a tension or changed file.

    Provides rich context including:
    - Change type analysis (structural, lexical, semantic)
    - Severity assessment
    - Likely causes of the tension
    - Suggested actions to fix the issue
    - Relevant code snippets from affected files
    - Step-by-step fix guidance

    This tool generates context that helps Claude provide intelligent
    fix suggestions based on the specific type of change detected.

    Args:
        tension_id: ID of a specific tension to analyze.
        file_path: Path to a changed file to analyze (uses latest delta).

    Returns:
        Rich context with analysis, snippets, and fix guidance.

    Examples:
        - Analyze a tension: tension_id="abc123"
        - Analyze a changed file: file_path="/path/to/changed.js"
    """
    with get_connection() as conn:
        cube = DeltaCodeCube(conn)
        return cube.get_suggestion_context(
            tension_id=tension_id,
            file_path=file_path,
        )

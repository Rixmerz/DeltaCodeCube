"""FastMCP server for DeltaCodeCube.

Multi-dimensional code indexing - represent code as points in 63D feature space
for similarity search, impact analysis, and change detection.
"""

from typing import Any

from fastmcp import FastMCP

from deltacodecube.db.database import get_connection
from deltacodecube.cube import DeltaCodeCube, TensionDetector

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


@mcp.tool()
def cube_export_html(
    output_path: str | None = None,
) -> dict[str, Any]:
    """
    Export an interactive HTML visualization of the code cube.

    Creates a self-contained HTML file with:
    - 3D scatter plot of all indexed files
    - Color-coded by semantic domain
    - Hover tooltips with file info
    - Contract/dependency lines
    - Pan, zoom, and rotate controls

    No external dependencies - all JavaScript is embedded.

    Args:
        output_path: Optional path to save the HTML file.
                    If not provided, returns HTML content.

    Returns:
        Dictionary with success status and file path or HTML content.
    """
    from deltacodecube.visualization import generate_html_visualization

    with get_connection() as conn:
        cube = DeltaCodeCube(conn)

        # Get data for visualization
        positions = cube.export_positions(format="3d")
        code_points = positions.get("points", [])

        # Get contracts
        contracts = cube.get_contracts(limit=500)

        # Get active tensions
        tension_detector = TensionDetector(conn)
        tensions = tension_detector.get_tensions(status="detected", limit=100)
        tensions_data = [t.to_dict() for t in tensions]

        # Generate HTML
        html = generate_html_visualization(
            code_points=code_points,
            contracts=contracts,
            tensions=tensions_data,
            output_path=output_path,
        )

        if output_path:
            return {
                "success": True,
                "message": f"HTML visualization saved to {output_path}",
                "path": output_path,
                "stats": {
                    "files": len(code_points),
                    "contracts": len(contracts),
                    "tensions": len(tensions_data),
                },
            }
        else:
            return {
                "success": True,
                "html_length": len(html),
                "html": html[:1000] + "..." if len(html) > 1000 else html,
                "stats": {
                    "files": len(code_points),
                    "contracts": len(contracts),
                    "tensions": len(tensions_data),
                },
            }


@mcp.tool()
def cube_get_temporal(
    path: str,
) -> dict[str, Any]:
    """
    Get temporal (git history) features for a file.

    Extracts metrics from git history:
    - file_age: Days since first commit (0-1)
    - change_frequency: Commits in last 90 days (0-1)
    - author_diversity: Unique authors (0-1)
    - days_since_change: Recency of changes (0-1, higher = more recent)
    - stability_score: Inverse of change frequency (0-1)

    Useful for identifying:
    - Hot spots (frequently changed files)
    - Stale code (old, unchanged files)
    - Ownership patterns

    Args:
        path: Absolute path to the file.

    Returns:
        Dictionary with temporal features and interpretation.
    """
    from deltacodecube.cube.features.temporal import extract_temporal_features, get_feature_names

    features = extract_temporal_features(path)
    names = get_feature_names()

    # Build feature dictionary
    feature_dict = {name: float(features[i]) for i, name in enumerate(names)}

    # Interpretation
    interpretation = []
    if feature_dict["change_frequency"] > 0.5:
        interpretation.append("Hot spot: This file changes frequently")
    if feature_dict["days_since_change"] < 0.2:
        interpretation.append("Stale: This file hasn't been changed recently")
    if feature_dict["author_diversity"] > 0.5:
        interpretation.append("Shared ownership: Multiple authors have contributed")
    if feature_dict["stability_score"] > 0.8:
        interpretation.append("Stable: This file rarely changes")

    return {
        "path": path,
        "features": feature_dict,
        "interpretation": interpretation or ["No notable patterns detected"],
    }


@mcp.tool()
def cube_analyze_graph(
    top_n: int = 10,
) -> dict[str, Any]:
    """
    Analyze the dependency graph and compute centrality metrics.

    Computes graph-based metrics for all indexed files:
    - PageRank: Importance based on what depends on the file
    - Hub score: Files that aggregate many dependencies
    - Authority score: Core files that others depend on
    - Betweenness: Files that are bridges between modules

    Returns top files for each metric and summary statistics.

    Args:
        top_n: Number of top files to return for each metric.

    Returns:
        Graph analysis with centrality metrics and top files.

    Example insights:
        - High PageRank = Critical module, changes affect many
        - High Hub = Index/barrel file, aggregates exports
        - High Authority = Core utility, foundational code
        - High Betweenness = Bridge, breaking this isolates modules
    """
    from deltacodecube.cube.graph import analyze_dependency_graph

    with get_connection() as conn:
        return analyze_dependency_graph(conn, top_n=top_n)


@mcp.tool()
def cube_get_centrality(
    path: str,
) -> dict[str, Any]:
    """
    Get centrality metrics for a specific file.

    Returns graph-based importance metrics:
    - pagerank: How important is this file (0-1)
    - hub_score: Is this an aggregator file (0-1)
    - authority_score: Is this a core utility (0-1)
    - betweenness: Is this a bridge between modules (0-1)
    - in_degree: How many files depend on this
    - out_degree: How many files this depends on

    Also provides human-readable interpretation.

    Args:
        path: Absolute path to the file.

    Returns:
        Centrality metrics and interpretation.
    """
    from deltacodecube.cube.graph import get_file_centrality

    with get_connection() as conn:
        result = get_file_centrality(conn, path)
        if result is None:
            return {
                "error": f"File not found in index: {path}",
                "suggestion": "Index the file first with cube_index_file",
            }
        return result


@mcp.tool()
def cube_detect_smells() -> dict[str, Any]:
    """
    Detect code smells in the indexed codebase.

    Analyzes the dependency graph and code metrics to find:
    - God Files: Too many responsibilities (high dependencies + complexity)
    - Orphans: Isolated files with no connections
    - Circular Dependencies: A imports B imports A
    - Feature Envy: Heavy imports from a single module
    - Hub Overload: Too many outgoing dependencies
    - Unstable Interfaces: Critical files that change too often
    - Dead Code Candidates: Unused files with no activity

    Returns smells sorted by severity (critical, high, medium, low).

    Returns:
        Summary with total smells, breakdown by type/severity, and details.

    Example output:
        {
            "total_smells": 5,
            "by_severity": {"high": 2, "medium": 3},
            "smells": [
                {
                    "type": "god_file",
                    "severity": "high",
                    "file_name": "database.js",
                    "description": "God File: 12 files depend on this...",
                    "suggestion": "Consider splitting..."
                }
            ]
        }
    """
    from deltacodecube.cube.smells import get_smell_summary

    with get_connection() as conn:
        return get_smell_summary(conn)


@mcp.tool()
def cube_cluster_files(
    k: int | None = None,
) -> dict[str, Any]:
    """
    Cluster files by similarity using K-means on feature vectors.

    Automatically groups similar files based on their 86D feature vectors.
    Uses K-means clustering with automatic K selection via elbow method.

    Returns:
        - Clusters with names, characteristics, and member files
        - Outliers (files that don't fit well in any cluster)
        - Misclassified files (might belong to different cluster)
        - Silhouette score (clustering quality, -1 to 1)

    Args:
        k: Number of clusters. If None, finds optimal K automatically.

    Returns:
        Clustering results with clusters and quality metrics.

    Example use cases:
        - Discover natural groupings in codebase
        - Find files that should be reorganized
        - Identify outliers that don't fit patterns
    """
    from deltacodecube.cube.clustering import cluster_codebase

    with get_connection() as conn:
        return cluster_codebase(conn, k=k)


@mcp.tool()
def cube_get_suggestions() -> dict[str, Any]:
    """
    Get prioritized refactoring suggestions for the codebase.

    Combines analysis from graph, smells, clustering, and tensions to provide
    actionable refactoring suggestions sorted by priority and impact.

    Suggestion types:
        - split: Divide large files into smaller ones
        - merge: Combine related small files
        - move: Relocate file to better module
        - extract: Pull shared code into utility
        - stabilize: Add protection to critical interfaces
        - remove: Delete dead code
        - decouple: Break circular/tight dependencies

    Each suggestion includes:
        - Priority and impact/effort estimates
        - Target files
        - Rationale (why this refactoring is suggested)
        - Step-by-step instructions
        - Supporting metrics

    Returns:
        Prioritized suggestions with summary by action and priority.

    Example output:
        {
            "total_suggestions": 5,
            "by_action": {"split": 2, "move": 2, "remove": 1},
            "by_priority": {"high": 2, "medium": 2, "low": 1},
            "suggestions": [
                {
                    "action": "split",
                    "priority": "high",
                    "target_files": ["database.js"],
                    "description": "Split database.js into smaller modules",
                    "steps": ["1. Analyze...", "2. Group...", ...]
                }
            ]
        }
    """
    from deltacodecube.cube.advisor import get_refactoring_suggestions

    with get_connection() as conn:
        return get_refactoring_suggestions(conn)


@mcp.tool()
def cube_simulate_wave(
    source_path: str,
    intensity: float = 1.0,
) -> dict[str, Any]:
    """
    Simulate a tension wave from a source file.

    When a file changes, this simulates how the "wave" of potential impact
    propagates through dependent files. Intensity attenuates with distance
    and domain boundaries.

    Use this to:
        - Predict which files will need review after a change
        - Understand the ripple effect of modifications
        - Identify natural boundaries where impact stops
        - Prioritize code review order

    Args:
        source_path: Path to the file that changed (or will change).
        intensity: Initial wave intensity (0.0-1.0, default 1.0).

    Returns:
        Wave simulation with affected files, boundaries, and review order.

    Example output:
        {
            "source_file": "database.js",
            "total_affected": 7,
            "max_depth": 3,
            "boundaries": ["api.js", "sender.js"],
            "review_order": [
                {"priority": 1, "file": "settings.js", "intensity": 0.6},
                {"priority": 2, "file": "history.js", "intensity": 0.36}
            ]
        }
    """
    from deltacodecube.cube.waves import simulate_tension_wave

    with get_connection() as conn:
        return simulate_tension_wave(conn, source_path, intensity)


@mcp.tool()
def cube_predict_impact(
    path: str,
) -> dict[str, Any]:
    """
    Predict the impact of changing a file.

    Analyzes how changes to this file will propagate through the codebase
    and provides a risk assessment with recommendations.

    Returns:
        - Risk level (low, medium, high)
        - Number of affected files
        - High/medium impact file counts
        - Natural boundaries where impact stops
        - Recommendation for review process
        - Prioritized review order

    Args:
        path: Path to the file.

    Returns:
        Impact prediction with risk assessment.

    Example output:
        {
            "file": "database.js",
            "risk_level": "high",
            "total_affected": 12,
            "high_impact_files": 5,
            "recommendation": "Consider splitting into smaller PRs",
            "review_order": [...]
        }
    """
    from deltacodecube.cube.waves import predict_change_impact

    with get_connection() as conn:
        return predict_change_impact(conn, path)


@mcp.tool()
def cube_detect_clones() -> dict[str, Any]:
    """
    Detect code clones (duplicate/similar code) in the codebase.

    Uses Winnowing fingerprinting to find:
    - Exact clones: Identical code blocks
    - Parameterized clones: Same structure, different variable names
    - Near-miss clones: Similar code with modifications

    Returns:
        Clone detection results with similarity scores.

    Example output:
        {
            "total_clones": 5,
            "by_type": {"exact": 1, "parameterized": 2, "near-miss": 2},
            "clones": [
                {"file_a": "auth.js", "file_b": "login.js", "similarity": 0.85}
            ]
        }
    """
    from deltacodecube.cube.clones import detect_code_clones

    with get_connection() as conn:
        return detect_code_clones(conn)


@mcp.tool()
def cube_get_debt() -> dict[str, Any]:
    """
    Calculate technical debt score for the codebase.

    Combines multiple factors into a debt score (0-100):
    - Complexity: Cyclomatic + Halstead complexity
    - Size: Files that are too large
    - Coupling: Too many dependencies
    - Duplication: Code clones
    - Staleness: Old unchanged code
    - Documentation: Low comment ratio
    - Smells: Code smells detected
    - Tensions: Unresolved tensions

    Grades: A (0-20), B (21-40), C (41-60), D (61-80), F (81-100)

    Returns:
        Debt analysis with scores, grades, and recommendations.

    Example output:
        {
            "codebase_score": 42.5,
            "codebase_grade": "C",
            "by_grade": {"A": 5, "B": 8, "C": 4, "D": 2, "F": 1},
            "top_debt_files": [...]
        }
    """
    from deltacodecube.cube.debt import calculate_technical_debt

    with get_connection() as conn:
        return calculate_technical_debt(conn)


@mcp.tool()
def cube_analyze_surface() -> dict[str, Any]:
    """
    Analyze the API surface of all modules.

    Identifies:
    - What functions/classes each module exports
    - Which modules are public vs private
    - Modules with high stability risk (many exports + many dependents)
    - Total API surface area

    Useful for:
    - Understanding which functions are public
    - Identifying modules where changes will have wide impact
    - Finding overly exposed modules

    Returns:
        Surface analysis with exports, import counts, and risk levels.
    """
    from deltacodecube.cube.surface import analyze_api_surface

    with get_connection() as conn:
        return analyze_api_surface(conn)


@mcp.tool()
def cube_detect_drift() -> dict[str, Any]:
    """
    Detect code drift - files that are diverging unexpectedly.

    Drift types:
    - Semantic: Files in same domain diverging in patterns
    - Contract: Dependent files moving apart from baseline
    - Temporal: Some files updated while related files are stale

    Useful for:
    - Finding inconsistent code evolution
    - Identifying files that need synchronization
    - Detecting modules growing apart

    Returns:
        Drift detections with severity and recommendations.
    """
    from deltacodecube.cube.drift import detect_drift

    with get_connection() as conn:
        return detect_drift(conn)


# =============================================================================
# Visualization Tools
# =============================================================================


@mcp.tool()
def cube_generate_timeline(
    project_path: str,
    output_path: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """
    Generate an interactive timeline visualization of code changes.

    Shows:
    - Code changes (deltas) over time
    - Tension creation/resolution events
    - Git commits
    - Activity patterns

    Outputs an HTML file that can be opened in any browser.

    Args:
        project_path: Path to the project root (for git history).
        output_path: Where to save HTML file. Default: project_path/deltacodecube_timeline.html
        limit: Maximum events to include (default: 100).

    Returns:
        Result with event counts and output file path.

    Example output:
        {
            "events_count": 45,
            "by_type": {"deltas": 20, "tensions": 10, "commits": 15},
            "output_path": "/project/deltacodecube_timeline.html"
        }
    """
    from deltacodecube.cube.visualizations.timeline import generate_timeline

    with get_connection() as conn:
        return generate_timeline(conn, project_path, output_path, limit)


@mcp.tool()
def cube_generate_matrix(
    project_path: str = ".",
    output_path: str | None = None,
) -> dict[str, Any]:
    """
    Generate an interactive dependency matrix visualization.

    Shows:
    - File dependencies as a color-coded grid
    - Rows depend on columns
    - Direct vs bidirectional dependencies
    - Distance-based coloring (close vs far)

    Click cells for relationship details.

    Args:
        project_path: Path to the project root.
        output_path: Where to save HTML file. Default: project_path/deltacodecube_matrix.html

    Returns:
        Result with file/dependency counts and output path.

    Example output:
        {
            "files_count": 25,
            "dependencies_count": 42,
            "bidirectional_count": 8,
            "output_path": "/project/deltacodecube_matrix.html"
        }
    """
    from deltacodecube.cube.visualizations.matrix import generate_dependency_matrix

    with get_connection() as conn:
        return generate_dependency_matrix(conn, output_path, project_path)


@mcp.tool()
def cube_generate_heatmap(
    project_path: str = ".",
    output_path: str | None = None,
) -> dict[str, Any]:
    """
    Generate a code heatmap visualization.

    Shows files as colored cells based on:
    - Activity (changes + tensions)
    - Complexity
    - Technical debt
    - Tension count

    Toggle between metrics. Grouped by domain.

    Args:
        project_path: Path to the project root.
        output_path: Where to save HTML file. Default: project_path/deltacodecube_heatmap.html

    Returns:
        Result with file counts, hotspots, and output path.

    Example output:
        {
            "files_count": 25,
            "hotspots": 3,
            "high_debt_files": 5,
            "output_path": "/project/deltacodecube_heatmap.html"
        }
    """
    from deltacodecube.cube.visualizations.heatmap import generate_heatmap

    with get_connection() as conn:
        return generate_heatmap(conn, output_path, project_path)


@mcp.tool()
def cube_generate_architecture(
    project_path: str = ".",
    output_path: str | None = None,
) -> dict[str, Any]:
    """
    Generate an interactive architecture diagram.

    Shows:
    - Force-directed graph of modules
    - Color-coded by domain (auth, db, api, ui, util)
    - Node size based on file size and importance
    - Dependency arrows between modules
    - Hub/Authority highlighting

    Pan, zoom, and hover for details.

    Args:
        project_path: Path to the project root.
        output_path: Where to save HTML file. Default: project_path/deltacodecube_architecture.html

    Returns:
        Result with node/link counts and output path.

    Example output:
        {
            "nodes_count": 25,
            "links_count": 42,
            "domains": {"api": 8, "ui": 10, "util": 7},
            "hubs": 3,
            "authorities": 5,
            "output_path": "/project/deltacodecube_architecture.html"
        }
    """
    from deltacodecube.cube.visualizations.architecture import generate_architecture

    with get_connection() as conn:
        return generate_architecture(conn, output_path, project_path)
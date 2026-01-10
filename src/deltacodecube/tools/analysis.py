"""Analysis tools for DeltaCodeCube."""

from typing import Any

from deltacodecube.db.database import get_connection


def register_analysis_tools(mcp):
    """Register analysis tools with MCP server."""

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

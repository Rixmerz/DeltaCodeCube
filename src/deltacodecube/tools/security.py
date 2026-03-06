"""Security MCP tools for DeltaCodeCube."""

from typing import Any

from deltacodecube.db.database import get_connection
from deltacodecube.utils import convert_numpy_types


def register_security_tools(mcp):
    """Register security analysis tools with MCP server."""

    # =========================================================================
    # Phase 1: SARIF Ingestion
    # =========================================================================

    @mcp.tool()
    def cube_ingest_sarif(
        sarif_path: str,
        source_tool: str | None = None,
    ) -> dict[str, Any]:
        """
        Ingest SARIF v2.1.0 security scan results into DCC.

        Parses SARIF output from tools like Semgrep, Trivy, CodeQL, etc.
        Maps findings to indexed code_points by file path.
        Deduplicates across repeated scans via fingerprinting.

        Args:
            sarif_path: Path to the SARIF JSON file.
            source_tool: Override scanner name (auto-detected from SARIF if omitted).

        Returns:
            Ingestion summary with new/deduplicated/mapped counts.
        """
        from deltacodecube.cube.security.sarif import SARIFIngester

        with get_connection() as conn:
            ingester = SARIFIngester(conn)
            return ingester.ingest_file(sarif_path, source_tool)

    @mcp.tool()
    def cube_get_findings(
        severity: str | None = None,
        status: str | None = None,
        file_path: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        Get security findings with optional filters.

        Returns findings sorted by severity (critical first), with summary stats.

        Args:
            severity: Filter by severity (critical, high, medium, low, info).
            status: Filter by status (open, confirmed, suppressed, fixed, false_positive).
            file_path: Filter by file path (partial match).
            limit: Maximum results (default 100).

        Returns:
            Filtered findings list and by_severity breakdown.
        """
        from deltacodecube.cube.security.sarif import get_findings

        with get_connection() as conn:
            return convert_numpy_types(get_findings(conn, severity, status, file_path, limit))

    @mcp.tool()
    def cube_finding_stats() -> dict[str, Any]:
        """
        Get aggregate statistics for all security findings.

        Returns breakdown by severity, status, and tool, plus top rules.
        """
        from deltacodecube.cube.security.sarif import get_finding_stats

        with get_connection() as conn:
            return convert_numpy_types(get_finding_stats(conn))

    @mcp.tool()
    def cube_suppress_finding(
        finding_id: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """
        Suppress a security finding (mark as accepted risk or false positive).

        Args:
            finding_id: ID of the finding to suppress.
            reason: Reason for suppression.

        Returns:
            Confirmation of suppression.
        """
        from deltacodecube.cube.security.sarif import suppress_finding

        with get_connection() as conn:
            return suppress_finding(conn, finding_id, reason)

    # =========================================================================
    # Phase 2: Scanner Orchestration
    # =========================================================================

    @mcp.tool()
    def cube_check_scanners() -> dict[str, Any]:
        """
        Check which security scanners are available on this system.

        Checks for Trivy and Semgrep installations.

        Returns:
            Scanner availability with paths and descriptions.
        """
        from deltacodecube.cube.security.scanners import ScannerOrchestrator

        with get_connection() as conn:
            orchestrator = ScannerOrchestrator(conn)
            return orchestrator.check_scanners()

    @mcp.tool()
    def cube_scan_project(
        project_path: str,
        scanners: list[str] | None = None,
        timeout: int = 300,
    ) -> dict[str, Any]:
        """
        Run security scanners on a project and ingest results.

        Runs available scanners (Trivy, Semgrep) via subprocess, collects SARIF
        output, and ingests findings into DCC. Gracefully skips unavailable scanners.

        Args:
            project_path: Path to the project to scan.
            scanners: List of scanner names to run (default: all available).
            timeout: Timeout per scanner in seconds (default: 300).

        Returns:
            Combined results with per-scanner status and finding counts.
        """
        from deltacodecube.cube.security.scanners import ScannerOrchestrator

        with get_connection() as conn:
            orchestrator = ScannerOrchestrator(conn)
            return convert_numpy_types(orchestrator.scan_project(project_path, scanners, timeout))

    # =========================================================================
    # Phase 3: Hybrid Risk Scoring
    # =========================================================================

    @mcp.tool()
    def cube_calculate_risks() -> dict[str, Any]:
        """
        Calculate hybrid risk scores for all open findings.

        Combines CVE severity with DCC's unique metrics:
        - CVE severity (35%): Raw vulnerability score
        - Tension (25%): Structural fragility between coupled files
        - Technical debt (20%): Code quality score
        - Centrality (20%): Graph importance (PageRank + betweenness)

        A medium CVE in tense, high-centrality code scores higher than
        a critical CVE in an isolated utility file.

        Risk grades: S (critical), A (high), B (medium), C (low), D (minimal).

        Returns:
            Risk distribution, grade breakdown, and top 20 risks.
        """
        from deltacodecube.cube.security.risk import get_risk_report

        with get_connection() as conn:
            return convert_numpy_types(get_risk_report(conn))

    @mcp.tool()
    def cube_get_risk_report() -> dict[str, Any]:
        """
        Get the full security risk report with hybrid scores.

        Same as cube_calculate_risks but recalculates fresh scores.

        Returns:
            Complete risk report with all findings scored and graded.
        """
        from deltacodecube.cube.security.risk import get_risk_report

        with get_connection() as conn:
            return convert_numpy_types(get_risk_report(conn))

    @mcp.tool()
    def cube_get_file_risk(
        path: str,
    ) -> dict[str, Any]:
        """
        Get hybrid risk report for a specific file.

        Shows all findings in the file with their hybrid risk scores,
        combining CVE severity with tension/debt/centrality context.

        Args:
            path: File path (partial match supported).

        Returns:
            File-level risk report with per-finding scores.
        """
        from deltacodecube.cube.security.risk import get_file_risk

        with get_connection() as conn:
            return convert_numpy_types(get_file_risk(conn, path))

    # =========================================================================
    # Phase 3b: Blast Radius
    # =========================================================================

    @mcp.tool()
    def cube_blast_radius(
        path: str,
    ) -> dict[str, Any]:
        """
        Simulate exploit blast radius from a vulnerable file.

        Extends wave propagation with security context: attenuation is
        REDUCED in high-tension nodes (attack amplified through stressed code).

        Shows how a compromised file could affect the rest of the codebase.

        Args:
            path: File path of the vulnerable file.

        Returns:
            Blast radius with affected files, amplification, and risk factors.
        """
        from deltacodecube.cube.security.blast_radius import BlastRadiusSimulator

        with get_connection() as conn:
            sim = BlastRadiusSimulator(conn)
            return convert_numpy_types(sim.blast_radius(path))

    @mcp.tool()
    def cube_attack_surface() -> dict[str, Any]:
        """
        Analyze the overall attack surface of the codebase.

        Identifies files that would cause maximum blast radius if compromised.
        Ranks entry points by composite risk (CVE * blast radius * tension).

        Returns:
            Attack surface analysis with ranked dangerous entry points.
        """
        from deltacodecube.cube.security.blast_radius import BlastRadiusSimulator

        with get_connection() as conn:
            sim = BlastRadiusSimulator(conn)
            return convert_numpy_types(sim.attack_surface())

    # =========================================================================
    # Phase 4a: Security Heatmap
    # =========================================================================

    @mcp.tool()
    def cube_generate_security_heatmap(
        project_path: str = ".",
        output_path: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate an interactive security risk heatmap visualization.

        Shows the codebase as a force-directed graph where:
        - Node COLOR = hybrid risk score (green=safe, red=critical)
        - Node SIZE = finding count + risk level
        - Edges = dependencies

        Outputs an HTML file that opens in any browser.

        Args:
            project_path: Project root path.
            output_path: Where to save HTML (default: project_path/dcc_security_heatmap.html).

        Returns:
            Generation result with node/edge counts and output path.
        """
        from deltacodecube.cube.visualizations.security_heatmap import generate_security_heatmap

        with get_connection() as conn:
            return generate_security_heatmap(conn, output_path, project_path)

    # =========================================================================
    # Phase 4b: Deduplication
    # =========================================================================

    @mcp.tool()
    def cube_deduplicate_findings() -> dict[str, Any]:
        """
        Group related findings and deduplicate.

        Groups by rule_id + file directory pattern. Creates finding_groups
        with representative findings for each cluster.

        Returns:
            Deduplication summary with group counts.
        """
        from deltacodecube.cube.security.dedup import deduplicate_findings

        with get_connection() as conn:
            return deduplicate_findings(conn)

    @mcp.tool()
    def cube_add_suppression(
        rule_id_pattern: str,
        file_pattern: str | None = None,
        reason: str = "",
    ) -> dict[str, Any]:
        """
        Add a suppression rule and apply to matching findings.

        Supports wildcard patterns for both rule_id and file_path.

        Args:
            rule_id_pattern: Pattern for rule_id (supports * wildcards).
            file_pattern: Optional file path pattern (supports * wildcards).
            reason: Reason for suppression.

        Returns:
            Number of findings suppressed.

        Examples:
            cube_add_suppression("python.lang.security.*", reason="False positive in tests")
            cube_add_suppression("*", "*/test/*", reason="Test files excluded")
        """
        from deltacodecube.cube.security.dedup import add_suppression_rule

        with get_connection() as conn:
            return add_suppression_rule(conn, rule_id_pattern, file_pattern, reason)

    @mcp.tool()
    def cube_finding_groups() -> dict[str, Any]:
        """
        Get all finding groups with their member counts.

        Returns groups created by cube_deduplicate_findings.

        Returns:
            Groups with counts and representative findings.
        """
        from deltacodecube.cube.security.dedup import get_finding_groups

        with get_connection() as conn:
            return get_finding_groups(conn)

    # =========================================================================
    # Phase 4c: Remediation
    # =========================================================================

    @mcp.tool()
    def cube_security_remediation(
        finding_id: str,
    ) -> dict[str, Any]:
        """
        Generate remediation context for a security finding.

        Provides rich context for Claude to generate intelligent fix suggestions:
        - CVE details and severity
        - Code snippets around the vulnerability
        - Related findings in the same file
        - Active tensions on the file
        - Dependent files that might be affected
        - "Dual fix" guidance: resolve CVE AND reduce tension simultaneously

        Args:
            finding_id: ID of the security finding.

        Returns:
            Rich remediation context for LLM-based fix generation.
        """
        from deltacodecube.cube.security.remediation import generate_remediation

        with get_connection() as conn:
            return convert_numpy_types(generate_remediation(conn, finding_id))

    # =========================================================================
    # Phase 5a: Security Gate
    # =========================================================================

    @mcp.tool()
    def cube_security_gate(
        max_grade: str = "B",
        max_open_criticals: int = 0,
        max_hybrid_score: float = 0.8,
        fail_on_new: bool = False,
    ) -> dict[str, Any]:
        """
        Run security quality gate check.

        Evaluates the codebase against configurable security thresholds.
        Designed for CI/CD pipeline integration.

        Args:
            max_grade: Maximum allowed risk grade (S/A/B/C/D, default B).
            max_open_criticals: Maximum open critical findings (default 0).
            max_hybrid_score: Maximum hybrid risk score (default 0.8).
            fail_on_new: Fail on any new findings in last 24h.

        Returns:
            Gate result with pass/fail, violations, and stats.
        """
        from deltacodecube.cli.gatekeeper import run_gate

        return run_gate(max_grade, max_open_criticals, max_hybrid_score, fail_on_new)

    # =========================================================================
    # Phase 5b: Cost Metrics
    # =========================================================================

    @mcp.tool()
    def cube_cost_report(
        hourly_rate: float = 75.0,
    ) -> dict[str, Any]:
        """
        Generate business cost report for security and debt remediation.

        Translates security risk and technical debt into:
        - Estimated fix hours and cost
        - Potential breach exposure (adjusted by hybrid risk)
        - ROI ratio (breach cost / fix cost)
        - Recommendations based on ROI

        Args:
            hourly_rate: Developer hourly rate in USD (default 75).

        Returns:
            Cost analysis with fix costs, breach exposure, and ROI.
        """
        from deltacodecube.cube.security.cost import cost_report

        with get_connection() as conn:
            return convert_numpy_types(cost_report(conn, hourly_rate))

    # =========================================================================
    # Phase 5c: Runtime Observability
    # =========================================================================

    @mcp.tool()
    def cube_record_execution(
        file_path: str,
        execution_count: int = 1,
        error_count: int = 0,
        avg_response_time_ms: float = 0.0,
    ) -> dict[str, Any]:
        """
        Record runtime execution data for a file.

        Tracks how often code runs, error rates, and response times.
        Used by the priority matrix to combine risk with runtime frequency.

        Args:
            file_path: File to record execution for.
            execution_count: Number of executions to add.
            error_count: Number of errors to add.
            avg_response_time_ms: Average response time.

        Returns:
            Confirmation of recorded data.
        """
        from deltacodecube.cube.security.observability import record_execution

        with get_connection() as conn:
            return record_execution(conn, file_path, execution_count, error_count, avg_response_time_ms)

    @mcp.tool()
    def cube_hot_zones(
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Get the hottest runtime zones (most executed files).

        Shows files ranked by execution count with error rates.

        Args:
            limit: Max results (default 20).

        Returns:
            Top executed files with execution/error counts.
        """
        from deltacodecube.cube.security.observability import hot_zones

        with get_connection() as conn:
            return convert_numpy_types(hot_zones(conn, limit))

    @mcp.tool()
    def cube_priority_matrix(
        limit: int = 30,
    ) -> dict[str, Any]:
        """
        Generate priority matrix combining security risk with runtime frequency.

        Formula: priority = hybrid_risk_score * log(1 + execution_count)

        Files that are BOTH risky AND frequently executed get highest priority.
        This is the ultimate prioritization tool for remediation.

        Args:
            limit: Max results (default 30).

        Returns:
            Priority-ranked findings combining risk with runtime data.
        """
        from deltacodecube.cube.security.observability import priority_matrix

        with get_connection() as conn:
            return convert_numpy_types(priority_matrix(conn, limit))

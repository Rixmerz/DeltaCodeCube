"""SARIF Ingestion Engine for DeltaCodeCube.

Parses SARIF v2.1.0 output from security scanners (Semgrep, Trivy, etc.)
and maps findings to existing code_points by file_path lookup.
Fingerprinting via md5(rule_id:file_path:start_line) for dedup across scans.
"""

import hashlib
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from deltacodecube.utils.logger import get_logger

logger = get_logger(__name__)

SEVERITY_MAP = {
    "error": "high",
    "warning": "medium",
    "note": "low",
    "none": "info",
}

CVSS_SEVERITY_SCORES = {
    "critical": 1.0,
    "high": 0.8,
    "medium": 0.5,
    "low": 0.25,
    "info": 0.1,
}


def _fingerprint(rule_id: str, file_path: str, start_line: int | None) -> str:
    """Generate dedup fingerprint for a finding."""
    raw = f"{rule_id}:{file_path}:{start_line or 0}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _normalize_severity(level: str, properties: dict | None = None) -> str:
    """Normalize SARIF severity level to our scale."""
    if properties:
        sec_severity = properties.get("security-severity", "")
        if sec_severity:
            try:
                score = float(sec_severity)
                if score >= 9.0:
                    return "critical"
                elif score >= 7.0:
                    return "high"
                elif score >= 4.0:
                    return "medium"
                elif score >= 0.1:
                    return "low"
                return "info"
            except (ValueError, TypeError):
                pass

    return SEVERITY_MAP.get(level, "medium")


class SARIFIngester:
    """Ingests SARIF v2.1.0 findings into the DCC database."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def ingest(self, sarif_data: dict | str, source_tool: str | None = None) -> dict[str, Any]:
        """Ingest SARIF data into security_findings table.

        Args:
            sarif_data: SARIF JSON as dict or string.
            source_tool: Override tool name (auto-detected from SARIF if None).

        Returns:
            Ingestion summary with counts.
        """
        if isinstance(sarif_data, str):
            sarif_data = json.loads(sarif_data)

        runs = sarif_data.get("runs", [])
        total_new = 0
        total_dedup = 0
        total_mapped = 0

        for run in runs:
            tool_name = source_tool or run.get("tool", {}).get("driver", {}).get("name", "unknown")
            rules_map = self._build_rules_map(run)
            results = run.get("results", [])

            for result in results:
                rule_id = result.get("ruleId", "unknown")
                rule_info = rules_map.get(rule_id, {})
                level = result.get("level", rule_info.get("defaultConfiguration", {}).get("level", "warning"))
                properties = result.get("properties", rule_info.get("properties", {}))
                severity = _normalize_severity(level, properties)

                message = result.get("message", {}).get("text", "")
                category = rule_info.get("properties", {}).get("tags", [None])[0] if rule_info.get("properties", {}).get("tags") else None

                # Extract CVSS score if available
                cvss = 0.0
                sec_sev = properties.get("security-severity", "")
                if sec_sev:
                    try:
                        cvss = float(sec_sev) / 10.0  # Normalize to 0-1
                    except (ValueError, TypeError):
                        cvss = CVSS_SEVERITY_SCORES.get(severity, 0.5)
                else:
                    cvss = CVSS_SEVERITY_SCORES.get(severity, 0.5)

                # Extract locations
                for location in result.get("locations", [{}]):
                    phys = location.get("physicalLocation", {})
                    artifact = phys.get("artifactLocation", {})
                    file_path = artifact.get("uri", "")

                    # Strip file:// prefix
                    if file_path.startswith("file://"):
                        file_path = file_path[7:]

                    region = phys.get("region", {})
                    start_line = region.get("startLine")
                    end_line = region.get("endLine", start_line)

                    fingerprint = result.get("fingerprints", {}).get("0") or _fingerprint(rule_id, file_path, start_line)

                    # Check dedup
                    existing = self.conn.execute(
                        "SELECT id FROM security_findings WHERE sarif_fingerprint = ?",
                        (fingerprint,),
                    ).fetchone()

                    if existing:
                        total_dedup += 1
                        continue

                    # Map to code_point
                    code_point_id = self._find_code_point(file_path)
                    if code_point_id:
                        total_mapped += 1

                    finding_id = uuid.uuid4().hex[:12]

                    self.conn.execute(
                        """
                        INSERT INTO security_findings
                            (id, source_tool, rule_id, severity, cvss_score, category,
                             file_path, start_line, end_line, code_point_id,
                             message, sarif_fingerprint, status, raw_sarif)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)
                        """,
                        (
                            finding_id, tool_name, rule_id, severity, cvss,
                            category, file_path, start_line, end_line,
                            code_point_id, message, fingerprint,
                            json.dumps(result),
                        ),
                    )
                    total_new += 1

        self.conn.commit()

        return {
            "new_findings": total_new,
            "deduplicated": total_dedup,
            "mapped_to_code_points": total_mapped,
            "total_processed": total_new + total_dedup,
        }

    def ingest_file(self, sarif_path: str, source_tool: str | None = None) -> dict[str, Any]:
        """Ingest SARIF from a file path.

        Args:
            sarif_path: Path to SARIF JSON file.
            source_tool: Override tool name.

        Returns:
            Ingestion summary.
        """
        path = Path(sarif_path)
        if not path.exists():
            return {"error": f"SARIF file not found: {sarif_path}"}

        data = json.loads(path.read_text(encoding="utf-8"))
        return self.ingest(data, source_tool)

    def _build_rules_map(self, run: dict) -> dict[str, dict]:
        """Build rule_id -> rule_info map from SARIF run."""
        rules = run.get("tool", {}).get("driver", {}).get("rules", [])
        return {r.get("id", ""): r for r in rules}

    def _find_code_point(self, file_path: str) -> str | None:
        """Find code_point_id by file_path (exact or suffix match)."""
        # Try exact match first
        row = self.conn.execute(
            "SELECT id FROM code_points WHERE file_path = ?",
            (file_path,),
        ).fetchone()
        if row:
            return row["id"]

        # Try suffix match
        row = self.conn.execute(
            "SELECT id FROM code_points WHERE file_path LIKE ?",
            (f"%{file_path}",),
        ).fetchone()
        if row:
            return row["id"]

        return None


def get_findings(
    conn: sqlite3.Connection,
    severity: str | None = None,
    status: str | None = None,
    file_path: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Get security findings with optional filters.

    Args:
        conn: Database connection.
        severity: Filter by severity.
        status: Filter by status.
        file_path: Filter by file path (partial match).
        limit: Max results.

    Returns:
        Findings list and summary.
    """
    conditions = []
    params: list[Any] = []

    if severity:
        conditions.append("severity = ?")
        params.append(severity)
    if status:
        conditions.append("status = ?")
        params.append(status)
    if file_path:
        conditions.append("file_path LIKE ?")
        params.append(f"%{file_path}%")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    cursor = conn.execute(
        f"""
        SELECT id, source_tool, rule_id, severity, cvss_score, category,
               file_path, start_line, end_line, code_point_id,
               message, status, created_at
        FROM security_findings
        {where}
        ORDER BY
            CASE severity
                WHEN 'critical' THEN 0
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
                ELSE 4
            END,
            created_at DESC
        LIMIT ?
        """,
        params + [limit],
    )
    findings = cursor.fetchall()

    # Stats
    stats_cursor = conn.execute(f"""
        SELECT severity, COUNT(*) as count
        FROM security_findings
        {where}
        GROUP BY severity
    """, params)
    by_severity = {r["severity"]: r["count"] for r in stats_cursor.fetchall()}

    return {
        "findings": findings,
        "count": len(findings),
        "by_severity": by_severity,
        "total": sum(by_severity.values()),
    }


def get_finding_stats(conn: sqlite3.Connection) -> dict[str, Any]:
    """Get aggregate statistics for all security findings."""
    by_severity = {}
    for row in conn.execute(
        "SELECT severity, COUNT(*) as count FROM security_findings GROUP BY severity"
    ).fetchall():
        by_severity[row["severity"]] = row["count"]

    by_status = {}
    for row in conn.execute(
        "SELECT status, COUNT(*) as count FROM security_findings GROUP BY status"
    ).fetchall():
        by_status[row["status"]] = row["count"]

    by_tool = {}
    for row in conn.execute(
        "SELECT source_tool, COUNT(*) as count FROM security_findings GROUP BY source_tool"
    ).fetchall():
        by_tool[row["source_tool"]] = row["count"]

    top_rules = conn.execute("""
        SELECT rule_id, severity, COUNT(*) as count
        FROM security_findings
        WHERE status = 'open'
        GROUP BY rule_id
        ORDER BY count DESC
        LIMIT 10
    """).fetchall()

    total = sum(by_severity.values())
    open_count = by_status.get("open", 0)

    return {
        "total_findings": total,
        "open_findings": open_count,
        "by_severity": by_severity,
        "by_status": by_status,
        "by_tool": by_tool,
        "top_rules": top_rules,
    }


def suppress_finding(
    conn: sqlite3.Connection,
    finding_id: str,
    reason: str = "",
) -> dict[str, Any]:
    """Suppress a finding (mark as false positive or accepted risk).

    Args:
        conn: Database connection.
        finding_id: ID of the finding to suppress.
        reason: Reason for suppression.

    Returns:
        Result of the operation.
    """
    cursor = conn.execute(
        """
        UPDATE security_findings
        SET status = 'suppressed', updated_at = datetime('now')
        WHERE id = ?
        """,
        (finding_id,),
    )
    conn.commit()

    if cursor.rowcount == 0:
        return {"error": f"Finding not found: {finding_id}"}

    return {"suppressed": finding_id, "reason": reason}

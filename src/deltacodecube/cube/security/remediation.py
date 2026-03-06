"""LLM Remediation Suggestions for DeltaCodeCube.

Follows pattern of cube/suggestions.py — generates rich context for Claude
to provide intelligent fix suggestions. Key differentiator: "dual fix" guidance
that resolves CVE AND reduces tension simultaneously.
"""

import sqlite3
from pathlib import Path
from typing import Any

from deltacodecube.cube.suggestions import extract_relevant_snippets
from deltacodecube.utils.logger import get_logger

logger = get_logger(__name__)


def generate_remediation(conn: sqlite3.Connection, finding_id: str) -> dict[str, Any]:
    """Generate rich remediation context for a security finding.

    Combines CVE details with code quality context (tension, debt, centrality)
    to provide "dual fix" guidance: resolve the vulnerability AND improve
    the surrounding code quality.

    Args:
        conn: Database connection.
        finding_id: ID of the security finding.

    Returns:
        Rich context for LLM-based remediation.
    """
    # Get finding details
    finding = conn.execute("""
        SELECT sf.*, sr.hybrid_risk_score, sr.risk_grade,
               sr.tension_score, sr.debt_score, sr.centrality_score
        FROM security_findings sf
        LEFT JOIN security_risks sr ON sf.id = sr.finding_id
        WHERE sf.id = ?
    """, (finding_id,)).fetchone()

    if not finding:
        return {"error": f"Finding not found: {finding_id}"}

    file_path = finding["file_path"]

    # Get code snippets
    snippets = extract_relevant_snippets(file_path, max_lines=80)

    # Get related findings in same file
    related = conn.execute("""
        SELECT id, rule_id, severity, start_line, message
        FROM security_findings
        WHERE file_path = ? AND id != ? AND status = 'open'
        ORDER BY start_line
    """, (file_path, finding_id)).fetchall()

    # Get dependent files that might be affected by fix
    dependents = conn.execute("""
        SELECT cp2.file_path, c.baseline_distance
        FROM contracts c
        JOIN code_points cp1 ON c.callee_id = cp1.id
        JOIN code_points cp2 ON c.caller_id = cp2.id
        WHERE cp1.file_path LIKE ?
    """, (f"%{file_path}%",)).fetchall()

    # Get active tensions on this file
    tensions = conn.execute("""
        SELECT t.tension_magnitude, t.suggested_action,
               cp.file_path as affected_file
        FROM tensions t
        JOIN contracts c ON t.contract_id = c.id
        JOIN code_points cp ON c.caller_id = cp.id
        WHERE c.callee_id = (
            SELECT id FROM code_points WHERE file_path LIKE ?
        ) AND t.status = 'detected'
        LIMIT 5
    """, (f"%{file_path}%",)).fetchall()

    # Build remediation context
    context = {
        "type": "security_remediation_context",
        "finding": {
            "id": finding["id"],
            "rule_id": finding["rule_id"],
            "severity": finding["severity"],
            "cvss_score": finding["cvss_score"],
            "category": finding["category"],
            "message": finding["message"],
            "location": {
                "file": file_path,
                "file_name": Path(file_path).name,
                "start_line": finding["start_line"],
                "end_line": finding["end_line"],
            },
        },
        "risk_context": {
            "hybrid_risk_score": finding.get("hybrid_risk_score"),
            "risk_grade": finding.get("risk_grade"),
            "tension_score": finding.get("tension_score"),
            "debt_score": finding.get("debt_score"),
            "centrality_score": finding.get("centrality_score"),
        },
        "code_snippets": snippets,
        "related_findings": related,
        "related_count": len(related),
        "dependent_files": [
            {"path": d["file_path"], "name": Path(d["file_path"]).name}
            for d in dependents
        ],
        "active_tensions": tensions,
    }

    # Generate dual-fix guidance
    context["dual_fix_guidance"] = _generate_dual_fix(finding, tensions, dependents)

    return context


def _generate_dual_fix(
    finding: dict,
    tensions: list[dict],
    dependents: list[dict],
) -> dict[str, Any]:
    """Generate dual-fix guidance: resolve CVE + reduce tension."""
    file_name = Path(finding["file_path"]).name
    severity = finding["severity"]
    rule_id = finding["rule_id"]

    guidance = {
        "summary": (
            f"Fix {severity} vulnerability ({rule_id}) in {file_name}. "
        ),
        "security_fix": {
            "priority": "immediate" if severity in ("critical", "high") else "planned",
            "steps": [
                f"1. Review the vulnerable code at line {finding.get('start_line', '?')}",
                f"2. Understand the vulnerability: {finding.get('message', 'See rule documentation')}",
                "3. Apply the fix following secure coding guidelines",
                "4. Verify the fix doesn't introduce regressions",
            ],
        },
        "tension_reduction": {
            "applicable": len(tensions) > 0,
            "steps": [],
        },
        "impact_notes": [],
    }

    if tensions:
        guidance["summary"] += (
            f"Additionally, this file has {len(tensions)} active tension(s) — "
            "fixing both issues together reduces future risk."
        )
        guidance["tension_reduction"]["steps"] = [
            "While fixing the vulnerability, also consider:",
            *[f"  - {t.get('suggested_action', 'Review tension')}" for t in tensions[:3]],
            "This 'dual fix' approach resolves the CVE and reduces structural fragility.",
        ]
    else:
        guidance["summary"] += "No active tensions on this file."

    if len(dependents) > 3:
        guidance["impact_notes"].append(
            f"Caution: {len(dependents)} files depend on this module. "
            "Test thoroughly after fixing."
        )

    if finding.get("centrality_score", 0) > 0.5:
        guidance["impact_notes"].append(
            "This is a high-centrality file — changes propagate widely. "
            "Consider a feature flag for the fix."
        )

    return guidance

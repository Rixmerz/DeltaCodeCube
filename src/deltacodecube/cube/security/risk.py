"""Hybrid Risk Scoring — "Security Tensions" for DeltaCodeCube.

The killer differentiator: contextual risk scoring that combines CVE severity
with DCC's unique tension, debt, and centrality metrics.

A medium CVE in tense, tightly-coupled code is more dangerous than a
critical CVE in an isolated utility file.

Algorithm:
    hybrid = cve_severity * 0.35 + tension * 0.25 + debt * 0.20 + centrality * 0.20

Risk grades:
    S: 0.80-1.00 (Critical — immediate action)
    A: 0.60-0.79 (High — fix this sprint)
    B: 0.40-0.59 (Medium — plan to fix)
    C: 0.20-0.39 (Low — backlog)
    D: 0.00-0.19 (Minimal — monitor)
"""

import sqlite3
from typing import Any

from deltacodecube.utils.logger import get_logger

logger = get_logger(__name__)

WEIGHTS = {
    "cve_severity": 0.35,
    "tension": 0.25,
    "debt": 0.20,
    "centrality": 0.20,
}


def _score_to_grade(score: float) -> str:
    if score >= 0.80:
        return "S"
    elif score >= 0.60:
        return "A"
    elif score >= 0.40:
        return "B"
    elif score >= 0.20:
        return "C"
    return "D"


class HybridRiskCalculator:
    """Calculates hybrid risk scores combining security + code quality metrics."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def calculate_all(self) -> dict[str, Any]:
        """Calculate hybrid risk for all open findings.

        Returns:
            Summary with risk distribution and top risks.
        """
        findings = self.conn.execute("""
            SELECT id, file_path, code_point_id, severity, cvss_score
            FROM security_findings
            WHERE status = 'open'
        """).fetchall()

        if not findings:
            return {"message": "No open findings to score", "total": 0}

        scored = 0
        by_grade: dict[str, int] = {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0}

        for finding in findings:
            risk = self._calculate_risk(finding)
            self._save_risk(finding["id"], finding.get("code_point_id"), risk)
            by_grade[risk["risk_grade"]] = by_grade.get(risk["risk_grade"], 0) + 1
            scored += 1

        # Get top risks
        top_risks = self.conn.execute("""
            SELECT sr.*, sf.rule_id, sf.severity, sf.file_path, sf.message
            FROM security_risks sr
            JOIN security_findings sf ON sr.finding_id = sf.id
            ORDER BY sr.hybrid_risk_score DESC
            LIMIT 20
        """).fetchall()

        return {
            "total_scored": scored,
            "by_grade": by_grade,
            "top_risks": top_risks,
            "weights": WEIGHTS,
        }

    def calculate_for_file(self, file_path: str) -> dict[str, Any]:
        """Calculate risk for all findings in a specific file.

        Args:
            file_path: Path to the file.

        Returns:
            File risk report.
        """
        findings = self.conn.execute("""
            SELECT id, file_path, code_point_id, severity, cvss_score
            FROM security_findings
            WHERE file_path LIKE ? AND status = 'open'
        """, (f"%{file_path}%",)).fetchall()

        if not findings:
            return {"file": file_path, "findings": 0, "message": "No open findings for this file"}

        risks = []
        for finding in findings:
            risk = self._calculate_risk(finding)
            self._save_risk(finding["id"], finding.get("code_point_id"), risk)
            risks.append({
                "finding_id": finding["id"],
                "rule_id": finding.get("rule_id", ""),
                **risk,
            })

        risks.sort(key=lambda r: r["hybrid_risk_score"], reverse=True)
        max_risk = risks[0]["hybrid_risk_score"] if risks else 0.0

        return {
            "file": file_path,
            "findings": len(risks),
            "max_risk_score": round(max_risk, 3),
            "max_risk_grade": _score_to_grade(max_risk),
            "risks": risks,
        }

    def _calculate_risk(self, finding: dict) -> dict[str, Any]:
        """Calculate hybrid risk for a single finding."""
        cve_score = finding.get("cvss_score", 0.0) or 0.0
        code_point_id = finding.get("code_point_id")
        file_path = finding.get("file_path", "")

        tension_score = self._get_tension_score(code_point_id, file_path)
        debt_score = self._get_debt_score(code_point_id, file_path)
        centrality_score = self._get_centrality_score(code_point_id, file_path)

        hybrid = (
            cve_score * WEIGHTS["cve_severity"]
            + tension_score * WEIGHTS["tension"]
            + debt_score * WEIGHTS["debt"]
            + centrality_score * WEIGHTS["centrality"]
        )

        # Clamp to 0-1
        hybrid = max(0.0, min(1.0, hybrid))

        return {
            "cve_severity_score": round(cve_score, 3),
            "tension_score": round(tension_score, 3),
            "debt_score": round(debt_score, 3),
            "centrality_score": round(centrality_score, 3),
            "hybrid_risk_score": round(hybrid, 3),
            "risk_grade": _score_to_grade(hybrid),
        }

    def _get_tension_score(self, code_point_id: str | None, file_path: str) -> float:
        """Get normalized tension score for a file (0-1)."""
        from deltacodecube.cube.tension import get_file_tension_score
        return get_file_tension_score(self.conn, file_path)

    def _get_debt_score(self, code_point_id: str | None, file_path: str) -> float:
        """Get normalized debt score for a file (0-1)."""
        from deltacodecube.cube.debt import get_file_debt_score
        return get_file_debt_score(self.conn, file_path)

    def _get_centrality_score(self, code_point_id: str | None, file_path: str) -> float:
        """Get normalized centrality score for a file (0-1)."""
        from deltacodecube.cube.graph import get_file_centrality_score
        return get_file_centrality_score(self.conn, file_path)

    def _save_risk(self, finding_id: str, code_point_id: str | None, risk: dict) -> None:
        """Save or update risk score in database."""
        self.conn.execute("""
            INSERT INTO security_risks
                (finding_id, code_point_id, cve_severity_score, tension_score,
                 debt_score, centrality_score, hybrid_risk_score, risk_grade)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(finding_id) DO UPDATE SET
                cve_severity_score = excluded.cve_severity_score,
                tension_score = excluded.tension_score,
                debt_score = excluded.debt_score,
                centrality_score = excluded.centrality_score,
                hybrid_risk_score = excluded.hybrid_risk_score,
                risk_grade = excluded.risk_grade,
                calculated_at = datetime('now')
        """, (
            finding_id, code_point_id,
            risk["cve_severity_score"], risk["tension_score"],
            risk["debt_score"], risk["centrality_score"],
            risk["hybrid_risk_score"], risk["risk_grade"],
        ))
        self.conn.commit()


def get_risk_report(conn: sqlite3.Connection) -> dict[str, Any]:
    """Get the full risk report.

    Returns:
        Risk distribution, top risks, and comparisons.
    """
    calculator = HybridRiskCalculator(conn)
    return calculator.calculate_all()


def get_file_risk(conn: sqlite3.Connection, file_path: str) -> dict[str, Any]:
    """Get risk report for a specific file."""
    calculator = HybridRiskCalculator(conn)
    return calculator.calculate_for_file(file_path)

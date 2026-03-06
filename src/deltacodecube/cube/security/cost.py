"""Business Cost Metrics for DeltaCodeCube.

Translates debt + risk into hours/cost estimates.
ROI calculation: potential breach cost / fix cost.
"""

import sqlite3
from typing import Any

from deltacodecube.utils.logger import get_logger

logger = get_logger(__name__)

# Cost assumptions (configurable)
DEFAULT_HOURLY_RATE = 75  # USD per developer hour
BREACH_COST_BY_SEVERITY = {
    "critical": 500_000,
    "high": 100_000,
    "medium": 25_000,
    "low": 5_000,
    "info": 1_000,
}
FIX_HOURS_BY_SEVERITY = {
    "critical": 16,
    "high": 8,
    "medium": 4,
    "low": 2,
    "info": 1,
}
DEBT_HOURS_PER_POINT = 0.5  # Hours per debt score point


def cost_report(
    conn: sqlite3.Connection,
    hourly_rate: float = DEFAULT_HOURLY_RATE,
) -> dict[str, Any]:
    """Generate business cost report combining security risk and technical debt.

    Args:
        conn: Database connection.
        hourly_rate: Developer hourly rate in USD.

    Returns:
        Cost analysis with ROI calculations.
    """
    # Security fix costs
    findings = conn.execute("""
        SELECT sf.id, sf.severity, sf.file_path,
               sr.hybrid_risk_score, sr.risk_grade, sr.debt_score
        FROM security_findings sf
        LEFT JOIN security_risks sr ON sf.id = sr.finding_id
        WHERE sf.status = 'open'
    """).fetchall()

    total_fix_hours = 0.0
    total_breach_exposure = 0.0
    by_severity: dict[str, dict] = {}

    for f in findings:
        sev = f["severity"]
        fix_hours = FIX_HOURS_BY_SEVERITY.get(sev, 4)
        breach_cost = BREACH_COST_BY_SEVERITY.get(sev, 25_000)

        # Adjust by hybrid risk: high-risk findings cost more to ignore
        risk_multiplier = 1.0 + (f.get("hybrid_risk_score") or 0.0)
        adjusted_breach = breach_cost * risk_multiplier

        total_fix_hours += fix_hours
        total_breach_exposure += adjusted_breach

        if sev not in by_severity:
            by_severity[sev] = {"count": 0, "fix_hours": 0, "breach_exposure": 0}
        by_severity[sev]["count"] += 1
        by_severity[sev]["fix_hours"] += fix_hours
        by_severity[sev]["breach_exposure"] += adjusted_breach

    total_fix_cost = total_fix_hours * hourly_rate

    # Debt remediation costs
    debt_findings = [f for f in findings if f.get("debt_score")]
    total_debt_score = sum(f.get("debt_score", 0) for f in debt_findings)
    debt_hours = total_debt_score * DEBT_HOURS_PER_POINT * 100  # debt_score is 0-1
    debt_cost = debt_hours * hourly_rate

    # ROI
    roi = (total_breach_exposure / total_fix_cost) if total_fix_cost > 0 else 0

    return {
        "summary": {
            "total_open_findings": len(findings),
            "total_fix_hours": round(total_fix_hours, 1),
            "total_fix_cost_usd": round(total_fix_cost, 2),
            "total_breach_exposure_usd": round(total_breach_exposure, 2),
            "roi_ratio": round(roi, 1),
            "hourly_rate_usd": hourly_rate,
        },
        "by_severity": by_severity,
        "debt_remediation": {
            "total_debt_score": round(total_debt_score, 2),
            "estimated_hours": round(debt_hours, 1),
            "estimated_cost_usd": round(debt_cost, 2),
        },
        "recommendation": _recommendation(roi, len(findings)),
    }


def _recommendation(roi: float, finding_count: int) -> str:
    if finding_count == 0:
        return "No open findings. Maintain current security posture."
    if roi > 50:
        return (
            f"ROI of {roi:.0f}x — immediate remediation strongly recommended. "
            "Breach exposure far exceeds fix cost."
        )
    if roi > 10:
        return (
            f"ROI of {roi:.0f}x — remediation recommended this quarter. "
            "Good return on security investment."
        )
    if roi > 1:
        return (
            f"ROI of {roi:.1f}x — plan remediation in roadmap. "
            "Moderate return on investment."
        )
    return "Low ROI — consider suppressing low-severity findings and focusing on critical items."

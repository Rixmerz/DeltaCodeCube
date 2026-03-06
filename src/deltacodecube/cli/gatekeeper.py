"""CLI Gatekeeper for DeltaCodeCube.

Enforces security quality gates in CI/CD pipelines.
Exit code 0 = pass, 1 = fail.

Gate rules:
- max_grade: Fail if any finding has risk grade higher than this
- max_open_criticals: Fail if more than N critical findings
- max_hybrid_score: Fail if any hybrid score exceeds threshold
- fail_on_new: Fail if any new findings since last scan
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from deltacodecube.db.database import init_database, get_database


def run_gate(
    max_grade: str = "B",
    max_open_criticals: int = 0,
    max_hybrid_score: float = 0.8,
    fail_on_new: bool = False,
    output_format: str = "text",
) -> dict[str, Any]:
    """Run the security gate check.

    Args:
        max_grade: Maximum allowed risk grade (S > A > B > C > D).
        max_open_criticals: Maximum allowed open critical findings.
        max_hybrid_score: Maximum allowed hybrid risk score.
        fail_on_new: Whether to fail on any new (unreviewed) findings.
        output_format: Output format ('text' or 'json').

    Returns:
        Gate result with pass/fail and details.
    """
    conn = get_database()

    grade_order = {"S": 4, "A": 3, "B": 2, "C": 1, "D": 0}
    max_grade_val = grade_order.get(max_grade, 2)

    violations: list[dict] = []

    # Check 1: Risk grades
    high_grades = conn.execute("""
        SELECT sr.risk_grade, sf.file_path, sf.rule_id, sf.severity,
               sr.hybrid_risk_score
        FROM security_risks sr
        JOIN security_findings sf ON sr.finding_id = sf.id
        WHERE sf.status = 'open'
    """).fetchall()

    for row in high_grades:
        grade_val = grade_order.get(row["risk_grade"], 0)
        if grade_val > max_grade_val:
            violations.append({
                "type": "grade_exceeded",
                "file": row["file_path"],
                "rule": row["rule_id"],
                "grade": row["risk_grade"],
                "max_allowed": max_grade,
            })

        if row["hybrid_risk_score"] > max_hybrid_score:
            violations.append({
                "type": "score_exceeded",
                "file": row["file_path"],
                "rule": row["rule_id"],
                "score": row["hybrid_risk_score"],
                "max_allowed": max_hybrid_score,
            })

    # Check 2: Critical findings count
    critical_count = conn.execute("""
        SELECT COUNT(*) as cnt FROM security_findings
        WHERE severity = 'critical' AND status = 'open'
    """).fetchone()["cnt"]

    if critical_count > max_open_criticals:
        violations.append({
            "type": "too_many_criticals",
            "count": critical_count,
            "max_allowed": max_open_criticals,
        })

    # Check 3: New findings
    if fail_on_new:
        new_count = conn.execute("""
            SELECT COUNT(*) as cnt FROM security_findings
            WHERE status = 'open'
            AND created_at > datetime('now', '-1 day')
        """).fetchone()["cnt"]

        if new_count > 0:
            violations.append({
                "type": "new_findings",
                "count": new_count,
            })

    passed = len(violations) == 0

    result = {
        "passed": passed,
        "violations": violations,
        "violation_count": len(violations),
        "gates": {
            "max_grade": max_grade,
            "max_open_criticals": max_open_criticals,
            "max_hybrid_score": max_hybrid_score,
            "fail_on_new": fail_on_new,
        },
        "stats": {
            "total_open": conn.execute(
                "SELECT COUNT(*) as cnt FROM security_findings WHERE status = 'open'"
            ).fetchone()["cnt"],
            "critical_count": critical_count,
        },
    }

    return result


def main() -> None:
    """CLI entry point for dcc-gate."""
    parser = argparse.ArgumentParser(
        description="DeltaCodeCube Security Gate",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  dcc-gate --max-grade B
  dcc-gate --max-open-criticals 0 --fail-on-new
  dcc-gate --max-hybrid-score 0.6 --format json
        """,
    )
    parser.add_argument("--max-grade", default="B", choices=["S", "A", "B", "C", "D"],
                        help="Maximum allowed risk grade (default: B)")
    parser.add_argument("--max-open-criticals", type=int, default=0,
                        help="Maximum open critical findings (default: 0)")
    parser.add_argument("--max-hybrid-score", type=float, default=0.8,
                        help="Maximum hybrid risk score (default: 0.8)")
    parser.add_argument("--fail-on-new", action="store_true",
                        help="Fail on any new findings in last 24h")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="Output format (default: text)")
    parser.add_argument("--db", default=None,
                        help="Path to DCC database (default: ~/.deltacodecube/dcc.db)")

    args = parser.parse_args()

    # Initialize database
    init_database(args.db)

    result = run_gate(
        max_grade=args.max_grade,
        max_open_criticals=args.max_open_criticals,
        max_hybrid_score=args.max_hybrid_score,
        fail_on_new=args.fail_on_new,
        output_format=args.format,
    )

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        if result["passed"]:
            print("PASSED - Security gate check passed")
            print(f"  Open findings: {result['stats']['total_open']}")
            print(f"  Critical: {result['stats']['critical_count']}")
        else:
            print(f"FAILED - {result['violation_count']} violation(s)")
            for v in result["violations"]:
                if v["type"] == "grade_exceeded":
                    print(f"  Grade {v['grade']} > {v['max_allowed']}: {v['file']} ({v['rule']})")
                elif v["type"] == "score_exceeded":
                    print(f"  Score {v['score']:.2f} > {v['max_allowed']}: {v['file']}")
                elif v["type"] == "too_many_criticals":
                    print(f"  {v['count']} critical findings (max: {v['max_allowed']})")
                elif v["type"] == "new_findings":
                    print(f"  {v['count']} new findings in last 24h")

    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()

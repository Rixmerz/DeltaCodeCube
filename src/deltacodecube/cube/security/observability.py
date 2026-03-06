"""Runtime Observability for DeltaCodeCube.

Tracks execution counts, error rates, and response times per code point.
Priority matrix: priority = hybrid_risk_score * log(1 + execution_count)
"""

import math
import sqlite3
from typing import Any

from deltacodecube.utils.logger import get_logger

logger = get_logger(__name__)


def record_execution(
    conn: sqlite3.Connection,
    file_path: str,
    execution_count: int = 1,
    error_count: int = 0,
    avg_response_time_ms: float = 0.0,
) -> dict[str, Any]:
    """Record runtime execution data for a file.

    Args:
        conn: Database connection.
        file_path: File path to record data for.
        execution_count: Number of executions to add.
        error_count: Number of errors to add.
        avg_response_time_ms: Average response time in ms.

    Returns:
        Updated runtime data.
    """
    # Find code_point_id
    cp = conn.execute(
        "SELECT id FROM code_points WHERE file_path LIKE ?",
        (f"%{file_path}%",),
    ).fetchone()

    if not cp:
        return {"error": f"File not in index: {file_path}"}

    code_point_id = cp["id"]

    # Upsert runtime zone
    existing = conn.execute(
        "SELECT * FROM runtime_zones WHERE code_point_id = ?",
        (code_point_id,),
    ).fetchone()

    if existing:
        new_exec = existing["execution_count"] + execution_count
        new_err = existing["error_count"] + error_count
        # Weighted average for response time
        if avg_response_time_ms > 0 and existing["avg_response_time_ms"] > 0:
            total_exec = existing["execution_count"] + execution_count
            new_avg = (
                existing["avg_response_time_ms"] * existing["execution_count"]
                + avg_response_time_ms * execution_count
            ) / total_exec
        else:
            new_avg = avg_response_time_ms or existing["avg_response_time_ms"]

        conn.execute("""
            UPDATE runtime_zones
            SET execution_count = ?, error_count = ?,
                avg_response_time_ms = ?, last_recorded_at = datetime('now')
            WHERE code_point_id = ?
        """, (new_exec, new_err, new_avg, code_point_id))
    else:
        conn.execute("""
            INSERT INTO runtime_zones
                (code_point_id, execution_count, error_count, avg_response_time_ms)
            VALUES (?, ?, ?, ?)
        """, (code_point_id, execution_count, error_count, avg_response_time_ms))

    conn.commit()

    return {
        "file": file_path,
        "code_point_id": code_point_id,
        "recorded": True,
    }


def hot_zones(conn: sqlite3.Connection, limit: int = 20) -> dict[str, Any]:
    """Get the hottest runtime zones (most executed files).

    Returns:
        Top files by execution count with error rates.
    """
    zones = conn.execute("""
        SELECT rz.*, cp.file_path
        FROM runtime_zones rz
        JOIN code_points cp ON rz.code_point_id = cp.id
        ORDER BY rz.execution_count DESC
        LIMIT ?
    """, (limit,)).fetchall()

    results = []
    for z in zones:
        error_rate = z["error_count"] / z["execution_count"] if z["execution_count"] > 0 else 0
        results.append({
            "file_path": z["file_path"],
            "execution_count": z["execution_count"],
            "error_count": z["error_count"],
            "error_rate": round(error_rate, 4),
            "avg_response_time_ms": round(z["avg_response_time_ms"], 2),
        })

    return {
        "total_tracked": len(zones),
        "hot_zones": results,
    }


def priority_matrix(conn: sqlite3.Connection, limit: int = 30) -> dict[str, Any]:
    """Generate priority matrix: risk * runtime frequency.

    priority = hybrid_risk_score * log(1 + execution_count)

    Files that are both risky AND frequently executed get highest priority.

    Returns:
        Priority-ranked files combining security risk with runtime data.
    """
    rows = conn.execute("""
        SELECT sr.hybrid_risk_score, sr.risk_grade,
               sf.file_path, sf.rule_id, sf.severity, sf.message,
               COALESCE(rz.execution_count, 0) as exec_count,
               COALESCE(rz.error_count, 0) as err_count
        FROM security_risks sr
        JOIN security_findings sf ON sr.finding_id = sf.id
        LEFT JOIN code_points cp ON sf.code_point_id = cp.id
        LEFT JOIN runtime_zones rz ON cp.id = rz.code_point_id
        WHERE sf.status = 'open'
    """).fetchall()

    if not rows:
        return {"message": "No data for priority matrix", "entries": []}

    entries = []
    for r in rows:
        risk = r["hybrid_risk_score"] or 0.0
        exec_count = r["exec_count"] or 0
        priority = risk * math.log(1 + exec_count) if exec_count > 0 else risk * 0.1

        entries.append({
            "file_path": r["file_path"],
            "rule_id": r["rule_id"],
            "severity": r["severity"],
            "risk_grade": r["risk_grade"],
            "hybrid_risk_score": round(risk, 3),
            "execution_count": exec_count,
            "priority_score": round(priority, 3),
            "message": r["message"],
        })

    entries.sort(key=lambda e: e["priority_score"], reverse=True)

    return {
        "total_entries": len(entries),
        "entries": entries[:limit],
        "formula": "priority = hybrid_risk_score * log(1 + execution_count)",
    }

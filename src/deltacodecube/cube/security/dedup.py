"""Deduplication & Smart Suppression for DeltaCodeCube.

Groups findings by rule_id + file pattern + code cluster similarity.
Heuristic auto-suppress for dead code / orphan nodes.
"""

import fnmatch
import sqlite3
from typing import Any

from deltacodecube.utils.logger import get_logger

logger = get_logger(__name__)


def deduplicate_findings(conn: sqlite3.Connection) -> dict[str, Any]:
    """Group related findings and identify duplicates.

    Groups by rule_id and file directory pattern, creating finding_groups
    with representative findings for each cluster.

    Returns:
        Deduplication summary.
    """
    findings = conn.execute("""
        SELECT id, rule_id, file_path, start_line, message
        FROM security_findings
        WHERE status = 'open'
        ORDER BY rule_id, file_path
    """).fetchall()

    if not findings:
        return {"message": "No open findings to deduplicate", "groups_created": 0}

    groups: dict[str, list[dict]] = {}
    for f in findings:
        # Group key: rule_id + directory
        dir_path = "/".join(f["file_path"].split("/")[:-1])
        key = f"{f['rule_id']}:{dir_path}"
        groups.setdefault(key, []).append(f)

    created = 0
    for key, members in groups.items():
        if len(members) < 2:
            continue

        representative = members[0]

        # Insert or update group
        conn.execute("""
            INSERT INTO finding_groups (group_key, rule_id, representative_finding_id, count)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(group_key) DO UPDATE SET
                count = excluded.count,
                representative_finding_id = excluded.representative_finding_id
        """, (key, representative["rule_id"], representative["id"], len(members)))

        group_id = conn.execute(
            "SELECT id FROM finding_groups WHERE group_key = ?", (key,)
        ).fetchone()["id"]

        # Link members
        for member in members:
            conn.execute("""
                INSERT OR IGNORE INTO finding_group_members (group_id, finding_id)
                VALUES (?, ?)
            """, (group_id, member["id"]))

        created += 1

    conn.commit()

    return {
        "total_findings": len(findings),
        "groups_created": created,
        "findings_grouped": sum(len(m) for m in groups.values() if len(m) >= 2),
        "unique_rules": len(set(f["rule_id"] for f in findings)),
    }


def add_suppression_rule(
    conn: sqlite3.Connection,
    rule_id_pattern: str,
    file_pattern: str | None = None,
    reason: str = "",
) -> dict[str, Any]:
    """Add a suppression rule and apply it to matching findings.

    Args:
        conn: Database connection.
        rule_id_pattern: Pattern for rule_id (supports * wildcards).
        file_pattern: Optional file path pattern (supports * wildcards).
        reason: Reason for suppression.

    Returns:
        Number of findings suppressed.
    """
    conn.execute("""
        INSERT INTO suppression_rules (rule_id_pattern, file_pattern, reason)
        VALUES (?, ?, ?)
    """, (rule_id_pattern, file_pattern, reason))

    # Apply to existing findings
    findings = conn.execute("""
        SELECT id, rule_id, file_path
        FROM security_findings
        WHERE status = 'open'
    """).fetchall()

    suppressed = 0
    for f in findings:
        if not fnmatch.fnmatch(f["rule_id"], rule_id_pattern):
            continue
        if file_pattern and not fnmatch.fnmatch(f["file_path"], file_pattern):
            continue

        conn.execute("""
            UPDATE security_findings
            SET status = 'suppressed', updated_at = datetime('now')
            WHERE id = ?
        """, (f["id"],))
        suppressed += 1

    conn.commit()

    return {
        "rule_id_pattern": rule_id_pattern,
        "file_pattern": file_pattern,
        "reason": reason,
        "findings_suppressed": suppressed,
    }


def auto_suppress_dead_code(conn: sqlite3.Connection) -> dict[str, Any]:
    """Auto-suppress findings in dead code / orphan files.

    Identifies files with no dependencies (orphans) and suppresses
    their findings with lower priority.

    Returns:
        Count of auto-suppressed findings.
    """
    # Find orphan code points (no contracts referencing them)
    orphans = conn.execute("""
        SELECT cp.file_path
        FROM code_points cp
        LEFT JOIN contracts c1 ON cp.id = c1.caller_id
        LEFT JOIN contracts c2 ON cp.id = c2.callee_id
        WHERE c1.id IS NULL AND c2.id IS NULL
    """).fetchall()

    orphan_paths = {r["file_path"] for r in orphans}
    suppressed = 0

    for path in orphan_paths:
        cursor = conn.execute("""
            UPDATE security_findings
            SET status = 'suppressed', updated_at = datetime('now')
            WHERE file_path = ? AND status = 'open'
        """, (path,))
        suppressed += cursor.rowcount

    conn.commit()

    return {
        "orphan_files": len(orphan_paths),
        "findings_suppressed": suppressed,
        "reason": "auto-suppressed: findings in dead/orphan code",
    }


def get_finding_groups(conn: sqlite3.Connection) -> dict[str, Any]:
    """Get all finding groups with their members.

    Returns:
        Groups with counts and representative findings.
    """
    groups = conn.execute("""
        SELECT fg.*, sf.rule_id as rep_rule, sf.severity as rep_severity,
               sf.file_path as rep_file, sf.message as rep_message
        FROM finding_groups fg
        LEFT JOIN security_findings sf ON fg.representative_finding_id = sf.id
        ORDER BY fg.count DESC
    """).fetchall()

    return {
        "total_groups": len(groups),
        "groups": groups,
    }

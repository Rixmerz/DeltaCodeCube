"""Sequential migration runner for DeltaCodeCube.

Manages schema_version table and runs migrations in order.
Each migration is idempotent (uses IF NOT EXISTS).
"""

import sqlite3
from typing import Any

from deltacodecube.utils.logger import get_logger

logger = get_logger(__name__)


MIGRATIONS: list[tuple[int, str, str]] = [
    # (version, description, sql)
    (1, "security_findings table", """
        CREATE TABLE IF NOT EXISTS security_findings (
            id TEXT PRIMARY KEY,
            source_tool TEXT NOT NULL,
            rule_id TEXT NOT NULL,
            severity TEXT NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),
            cvss_score REAL DEFAULT 0.0,
            category TEXT,
            file_path TEXT NOT NULL,
            start_line INTEGER,
            end_line INTEGER,
            code_point_id TEXT REFERENCES code_points(id) ON DELETE SET NULL,
            message TEXT,
            sarif_fingerprint TEXT UNIQUE,
            status TEXT NOT NULL DEFAULT 'open'
                CHECK (status IN ('open', 'confirmed', 'suppressed', 'fixed', 'false_positive')),
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            raw_sarif TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_findings_file ON security_findings(file_path);
        CREATE INDEX IF NOT EXISTS idx_findings_severity ON security_findings(severity);
        CREATE INDEX IF NOT EXISTS idx_findings_status ON security_findings(status);
        CREATE INDEX IF NOT EXISTS idx_findings_rule ON security_findings(rule_id);
        CREATE INDEX IF NOT EXISTS idx_findings_code_point ON security_findings(code_point_id);
    """),
    (2, "security_risks table", """
        CREATE TABLE IF NOT EXISTS security_risks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            finding_id TEXT NOT NULL REFERENCES security_findings(id) ON DELETE CASCADE,
            code_point_id TEXT REFERENCES code_points(id) ON DELETE SET NULL,
            cve_severity_score REAL NOT NULL DEFAULT 0.0,
            tension_score REAL NOT NULL DEFAULT 0.0,
            debt_score REAL NOT NULL DEFAULT 0.0,
            centrality_score REAL NOT NULL DEFAULT 0.0,
            hybrid_risk_score REAL NOT NULL DEFAULT 0.0,
            risk_grade TEXT NOT NULL DEFAULT 'D'
                CHECK (risk_grade IN ('S', 'A', 'B', 'C', 'D')),
            calculated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(finding_id)
        );
        CREATE INDEX IF NOT EXISTS idx_risks_grade ON security_risks(risk_grade);
        CREATE INDEX IF NOT EXISTS idx_risks_hybrid ON security_risks(hybrid_risk_score DESC);
    """),
    (3, "suppression_rules and finding_groups tables", """
        CREATE TABLE IF NOT EXISTS suppression_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id_pattern TEXT NOT NULL,
            file_pattern TEXT,
            reason TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS finding_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_key TEXT NOT NULL UNIQUE,
            rule_id TEXT NOT NULL,
            representative_finding_id TEXT REFERENCES security_findings(id) ON DELETE SET NULL,
            count INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS finding_group_members (
            group_id INTEGER NOT NULL REFERENCES finding_groups(id) ON DELETE CASCADE,
            finding_id TEXT NOT NULL REFERENCES security_findings(id) ON DELETE CASCADE,
            PRIMARY KEY (group_id, finding_id)
        );
    """),
    (4, "runtime_zones table", """
        CREATE TABLE IF NOT EXISTS runtime_zones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code_point_id TEXT NOT NULL REFERENCES code_points(id) ON DELETE CASCADE,
            execution_count INTEGER NOT NULL DEFAULT 0,
            error_count INTEGER NOT NULL DEFAULT 0,
            avg_response_time_ms REAL DEFAULT 0.0,
            last_recorded_at TEXT DEFAULT (datetime('now')),
            UNIQUE(code_point_id)
        );
        CREATE INDEX IF NOT EXISTS idx_runtime_zones_exec ON runtime_zones(execution_count DESC);
    """),
]


def run_migrations(conn: sqlite3.Connection) -> int:
    """Run pending migrations.

    Args:
        conn: SQLite connection.

    Returns:
        Number of migrations applied.
    """
    # Ensure schema_version table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            description TEXT,
            applied_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Get current version
    cursor = conn.execute("SELECT MAX(version) as v FROM schema_version")
    row = cursor.fetchone()
    current_version = (row["v"] if isinstance(row, dict) else row[0]) or 0

    applied = 0
    for version, description, sql in MIGRATIONS:
        if version > current_version:
            logger.info(f"Applying migration {version}: {description}")
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_version (version, description) VALUES (?, ?)",
                (version, description),
            )
            conn.commit()
            applied += 1
            logger.info(f"Migration {version} applied successfully")

    if applied:
        logger.info(f"Applied {applied} migration(s), now at version {current_version + applied}")
    else:
        logger.debug(f"Schema up to date at version {current_version}")

    return applied

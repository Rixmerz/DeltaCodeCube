"""Scanner Orchestration for DeltaCodeCube.

Runs Trivy and Semgrep via subprocess, collects SARIF output,
and feeds it into the SARIFIngester. Gracefully degrades if tools not installed.
"""

import json
import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from deltacodecube.cube.security.sarif import SARIFIngester
from deltacodecube.utils.logger import get_logger

logger = get_logger(__name__)


SCANNERS = {
    "trivy": {
        "binary": "trivy",
        "cmd": lambda path, out: [
            "trivy", "fs", "--format", "sarif",
            "--output", out, str(path),
        ],
        "description": "Trivy vulnerability/misconfiguration scanner",
    },
    "semgrep": {
        "binary": "semgrep",
        "cmd": lambda path, out: [
            "semgrep", "--config", "auto", "--sarif",
            "--output", out, str(path),
        ],
        "description": "Semgrep SAST scanner",
    },
}


class ScannerOrchestrator:
    """Orchestrates external security scanners and ingests their SARIF output."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.ingester = SARIFIngester(conn)

    def check_scanners(self) -> dict[str, Any]:
        """Check which scanners are available.

        Returns:
            Dict with scanner availability info.
        """
        available = {}
        for name, info in SCANNERS.items():
            binary = shutil.which(info["binary"])
            available[name] = {
                "installed": binary is not None,
                "path": binary,
                "description": info["description"],
            }

        return {
            "scanners": available,
            "available_count": sum(1 for s in available.values() if s["installed"]),
            "total_count": len(SCANNERS),
        }

    def scan_project(
        self,
        project_path: str,
        scanners: list[str] | None = None,
        timeout: int = 300,
    ) -> dict[str, Any]:
        """Run security scanners on a project.

        Args:
            project_path: Path to the project to scan.
            scanners: List of scanner names to run. If None, run all available.
            timeout: Timeout per scanner in seconds.

        Returns:
            Combined scan results.
        """
        path = Path(project_path)
        if not path.exists():
            return {"error": f"Project path not found: {project_path}"}

        results: dict[str, Any] = {
            "project": str(path),
            "scanners_run": [],
            "scanners_skipped": [],
            "scanners_failed": [],
            "total_new_findings": 0,
            "total_deduplicated": 0,
        }

        scanner_names = scanners or list(SCANNERS.keys())

        for name in scanner_names:
            if name not in SCANNERS:
                results["scanners_skipped"].append({"name": name, "reason": "unknown scanner"})
                continue

            info = SCANNERS[name]
            binary = shutil.which(info["binary"])
            if not binary:
                results["scanners_skipped"].append({"name": name, "reason": "not installed"})
                continue

            result = self._run_scanner(name, info, path, timeout)
            if "error" in result:
                results["scanners_failed"].append({"name": name, "error": result["error"]})
            else:
                results["scanners_run"].append({"name": name, **result})
                results["total_new_findings"] += result.get("new_findings", 0)
                results["total_deduplicated"] += result.get("deduplicated", 0)

        return results

    def _run_scanner(
        self,
        name: str,
        info: dict,
        project_path: Path,
        timeout: int,
    ) -> dict[str, Any]:
        """Run a single scanner and ingest its output."""
        with tempfile.NamedTemporaryFile(suffix=".sarif", delete=False, mode="w") as tmp:
            output_path = tmp.name

        try:
            cmd = info["cmd"](project_path, output_path)
            logger.info(f"Running {name}: {' '.join(cmd)}")

            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(project_path),
            )

            # Some scanners return non-zero when findings exist
            sarif_file = Path(output_path)
            if not sarif_file.exists() or sarif_file.stat().st_size == 0:
                if proc.returncode != 0:
                    return {"error": f"Scanner failed: {proc.stderr[:500]}"}
                return {"error": "No SARIF output produced"}

            sarif_data = json.loads(sarif_file.read_text(encoding="utf-8"))
            ingest_result = self.ingester.ingest(sarif_data, source_tool=name)

            return {
                "exit_code": proc.returncode,
                **ingest_result,
            }

        except subprocess.TimeoutExpired:
            return {"error": f"Scanner timed out after {timeout}s"}
        except json.JSONDecodeError as e:
            return {"error": f"Invalid SARIF output: {e}"}
        except Exception as e:
            return {"error": str(e)}
        finally:
            Path(output_path).unlink(missing_ok=True)

"""Blast Radius / Attack Propagation for DeltaCodeCube.

Extends the wave propagation model from cube/waves.py to simulate
exploit propagation through the dependency graph. Key difference:
attenuation is REDUCED in high-tension nodes (attack amplified
through stressed code).

A vulnerability in a high-tension, high-centrality file has a
much larger blast radius than one in an isolated utility.
"""

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from deltacodecube.cube.graph import DependencyGraph
from deltacodecube.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BlastNode:
    """A node reached by exploit propagation."""
    file_path: str
    file_name: str
    exploit_intensity: float
    distance: int
    tension_amplified: bool
    risk_factors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "file_name": self.file_name,
            "exploit_intensity": round(self.exploit_intensity, 4),
            "distance": self.distance,
            "tension_amplified": self.tension_amplified,
            "risk_factors": self.risk_factors,
        }


class BlastRadiusSimulator:
    """Simulates exploit propagation through stressed dependency graph."""

    BASE_ATTENUATION = 0.5
    TENSION_AMPLIFICATION = 1.5  # High-tension nodes amplify propagation
    INTENSITY_THRESHOLD = 0.03

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.graph = DependencyGraph(conn)
        self.graph.build_graph()
        self.graph.compute_pagerank()
        self._tension_cache: dict[str, float] = {}
        self._load_tensions()

    def _load_tensions(self) -> None:
        """Pre-load tension scores per file."""
        rows = self.conn.execute("""
            SELECT cp.file_path, COUNT(*) as tension_count,
                   AVG(t.tension_magnitude) as avg_tension
            FROM tensions t
            JOIN contracts c ON t.contract_id = c.id
            JOIN code_points cp ON c.callee_id = cp.id
            WHERE t.status = 'detected'
            GROUP BY cp.file_path
        """).fetchall()

        for row in rows:
            # Normalize: more tensions + higher magnitude = higher score
            score = min(1.0, (row["tension_count"] * 0.2) + (row["avg_tension"] or 0) * 0.5)
            self._tension_cache[row["file_path"]] = score

    def blast_radius(self, file_path: str) -> dict[str, Any]:
        """Simulate blast radius from a vulnerability in the given file.

        Args:
            file_path: Path to the file with the vulnerability.

        Returns:
            Blast radius analysis.
        """
        # Find source node
        source = None
        for node in self.graph.nodes.values():
            if node.file_path == file_path or node.file_path.endswith(file_path):
                source = node
                break

        if not source:
            return {"error": f"File not in dependency graph: {file_path}"}

        # BFS with tension-amplified propagation
        affected: list[BlastNode] = []
        visited = {source.id}
        queue = [(source.id, 1.0, 0)]

        while queue:
            current_id, intensity, distance = queue.pop(0)
            current = self.graph.nodes[current_id]

            if distance > 0:
                tension = self._tension_cache.get(current.file_path, 0.0)
                amplified = tension > 0.3
                factors = []
                if amplified:
                    factors.append(f"tension={tension:.2f}")
                if current.pagerank > 0.05:
                    factors.append(f"pagerank={current.pagerank:.3f}")
                if current.in_degree > 3:
                    factors.append(f"dependents={current.in_degree}")

                affected.append(BlastNode(
                    file_path=current.file_path,
                    file_name=current.name,
                    exploit_intensity=intensity,
                    distance=distance,
                    tension_amplified=amplified,
                    risk_factors=factors,
                ))

            # Propagate to dependents (reverse edges: who depends on this file)
            dependents = self.graph.reverse_adjacency.get(current_id, set())
            for dep_id in dependents:
                if dep_id in visited:
                    continue
                visited.add(dep_id)

                dep = self.graph.nodes[dep_id]
                dep_tension = self._tension_cache.get(dep.file_path, 0.0)

                # Attenuation reduced in high-tension nodes
                if dep_tension > 0.3:
                    attenuation = self.BASE_ATTENUATION * self.TENSION_AMPLIFICATION
                else:
                    attenuation = self.BASE_ATTENUATION

                new_intensity = intensity * attenuation
                if new_intensity < self.INTENSITY_THRESHOLD:
                    continue

                queue.append((dep_id, new_intensity, distance + 1))

        affected.sort(key=lambda n: n.exploit_intensity, reverse=True)

        high_risk = sum(1 for n in affected if n.exploit_intensity > 0.5)
        tension_amplified = sum(1 for n in affected if n.tension_amplified)

        return {
            "source_file": source.name,
            "source_path": source.file_path,
            "total_affected": len(affected),
            "high_risk_affected": high_risk,
            "tension_amplified_nodes": tension_amplified,
            "max_depth": max((n.distance for n in affected), default=0),
            "affected_files": [n.to_dict() for n in affected],
        }

    def attack_surface(self) -> dict[str, Any]:
        """Analyze the overall attack surface of the codebase.

        Identifies files that would cause maximum blast radius if compromised.

        Returns:
            Attack surface analysis with ranked entry points.
        """
        entry_points = []

        # Only analyze files that have security findings
        vuln_files = self.conn.execute("""
            SELECT DISTINCT file_path, COUNT(*) as finding_count,
                   MAX(cvss_score) as max_cvss
            FROM security_findings
            WHERE status = 'open'
            GROUP BY file_path
        """).fetchall()

        for vf in vuln_files:
            blast = self.blast_radius(vf["file_path"])
            if "error" in blast:
                continue

            entry_points.append({
                "file": Path(vf["file_path"]).name,
                "file_path": vf["file_path"],
                "vulnerability_count": vf["finding_count"],
                "max_cvss": vf["max_cvss"],
                "blast_radius": blast["total_affected"],
                "high_risk_blast": blast["high_risk_affected"],
                "tension_amplified": blast["tension_amplified_nodes"],
                "composite_risk": round(
                    (vf["max_cvss"] or 0) * 0.4
                    + min(blast["total_affected"] / 20.0, 1.0) * 0.3
                    + min(blast["tension_amplified_nodes"] / 5.0, 1.0) * 0.3,
                    3,
                ),
            })

        entry_points.sort(key=lambda e: e["composite_risk"], reverse=True)

        return {
            "total_vulnerable_files": len(entry_points),
            "entry_points": entry_points,
            "most_dangerous": entry_points[:5] if entry_points else [],
        }

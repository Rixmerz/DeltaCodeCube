"""
Graph Analysis for DeltaCodeCube.

Implements graph centrality metrics on the dependency graph:
- PageRank: Importance based on who depends on you
- Betweenness: How much of a "bridge" a node is
- HITS (Hub/Authority): Core modules vs. utility modules
- Degree centrality: In-degree (dependents) and out-degree (dependencies)

All algorithms implemented with numpy only (no networkx dependency).
"""

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from deltacodecube.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class GraphNode:
    """A node in the dependency graph."""
    id: str
    file_path: str
    name: str
    domain: str
    line_count: int = 0

    # Centrality metrics (computed)
    pagerank: float = 0.0
    hub_score: float = 0.0
    authority_score: float = 0.0
    betweenness: float = 0.0
    in_degree: int = 0
    out_degree: int = 0

    # Extended metrics (v2)
    clustering_coeff: float = 0.0
    closeness: float = 0.0
    community_embedding: np.ndarray = field(default_factory=lambda: np.zeros(2))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "file_path": self.file_path,
            "name": self.name,
            "domain": self.domain,
            "line_count": self.line_count,
            "pagerank": round(self.pagerank, 4),
            "hub_score": round(self.hub_score, 4),
            "authority_score": round(self.authority_score, 4),
            "betweenness": round(self.betweenness, 4),
            "in_degree": self.in_degree,
            "out_degree": self.out_degree,
            "clustering_coeff": round(self.clustering_coeff, 4),
            "closeness": round(self.closeness, 4),
        }


@dataclass
class GraphAnalysis:
    """Results of graph analysis."""
    nodes: list[GraphNode]
    edges: list[tuple[str, str]]  # (caller_id, callee_id)

    # Summary metrics
    total_nodes: int = 0
    total_edges: int = 0
    avg_in_degree: float = 0.0
    avg_out_degree: float = 0.0
    density: float = 0.0

    # Top nodes by metric
    top_pagerank: list[dict] = field(default_factory=list)
    top_hubs: list[dict] = field(default_factory=list)
    top_authorities: list[dict] = field(default_factory=list)
    top_betweenness: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_nodes": self.total_nodes,
            "total_edges": self.total_edges,
            "avg_in_degree": round(self.avg_in_degree, 2),
            "avg_out_degree": round(self.avg_out_degree, 2),
            "density": round(self.density, 4),
            "top_pagerank": self.top_pagerank,
            "top_hubs": self.top_hubs,
            "top_authorities": self.top_authorities,
            "top_betweenness": self.top_betweenness,
            "nodes": [n.to_dict() for n in self.nodes],
        }


class DependencyGraph:
    """
    Builds and analyzes the dependency graph from contracts.

    The graph is directed:
    - Edge A -> B means A imports/depends on B
    - In-degree of B = how many files depend on B (authority)
    - Out-degree of A = how many files A depends on (hub behavior)
    """

    def __init__(self, conn: sqlite3.Connection):
        """
        Initialize with database connection.

        Args:
            conn: SQLite connection with dict_factory row_factory.
        """
        self.conn = conn
        self.nodes: dict[str, GraphNode] = {}
        self.edges: list[tuple[str, str]] = []
        self.adjacency: dict[str, set[str]] = {}  # out-edges: node -> {targets}
        self.reverse_adjacency: dict[str, set[str]] = {}  # in-edges: node -> {sources}

    def build_graph(self) -> None:
        """Build the graph from database."""
        # Load all code points as nodes
        cursor = self.conn.execute("""
            SELECT id, file_path, line_count, semantic_features
            FROM code_points
        """)

        for row in cursor.fetchall():
            node_id = row["id"]
            file_path = row["file_path"]

            # Get domain from semantic features
            import json
            semantic = json.loads(row["semantic_features"])
            domains = ["auth", "db", "api", "ui", "util"]
            domain_idx = np.argmax(semantic[:len(domains)]) if semantic else 0
            domain = domains[domain_idx] if domain_idx < len(domains) else "unknown"

            self.nodes[node_id] = GraphNode(
                id=node_id,
                file_path=file_path,
                name=Path(file_path).name,
                domain=domain,
                line_count=row["line_count"],
            )
            self.adjacency[node_id] = set()
            self.reverse_adjacency[node_id] = set()

        # Load all contracts as edges
        cursor = self.conn.execute("""
            SELECT caller_id, callee_id
            FROM contracts
        """)

        for row in cursor.fetchall():
            caller_id = row["caller_id"]
            callee_id = row["callee_id"]

            if caller_id in self.nodes and callee_id in self.nodes:
                self.edges.append((caller_id, callee_id))
                self.adjacency[caller_id].add(callee_id)
                self.reverse_adjacency[callee_id].add(caller_id)

        # Calculate degree
        for node_id, node in self.nodes.items():
            node.out_degree = len(self.adjacency.get(node_id, set()))
            node.in_degree = len(self.reverse_adjacency.get(node_id, set()))

        logger.info(f"Built graph with {len(self.nodes)} nodes and {len(self.edges)} edges")

    def compute_pagerank(
        self,
        damping: float = 0.85,
        max_iterations: int = 100,
        tolerance: float = 1e-6,
    ) -> None:
        """
        Compute PageRank for all nodes.

        PageRank measures importance: nodes that are depended on by
        many important nodes have high PageRank.

        Args:
            damping: Damping factor (probability of following a link).
            max_iterations: Maximum iterations.
            tolerance: Convergence tolerance.
        """
        n = len(self.nodes)
        if n == 0:
            return

        node_ids = list(self.nodes.keys())
        id_to_idx = {nid: i for i, nid in enumerate(node_ids)}

        # Initialize PageRank uniformly
        pr = np.ones(n) / n

        for iteration in range(max_iterations):
            pr_new = np.ones(n) * (1 - damping) / n

            for i, node_id in enumerate(node_ids):
                # Get nodes that point to this node (reverse edges)
                sources = self.reverse_adjacency.get(node_id, set())

                for source_id in sources:
                    source_idx = id_to_idx[source_id]
                    out_degree = len(self.adjacency.get(source_id, set()))
                    if out_degree > 0:
                        pr_new[i] += damping * pr[source_idx] / out_degree

            # Check convergence
            diff = np.abs(pr_new - pr).sum()
            pr = pr_new

            if diff < tolerance:
                logger.debug(f"PageRank converged in {iteration + 1} iterations")
                break

        # Normalize and assign to nodes
        pr = pr / pr.sum() if pr.sum() > 0 else pr
        for i, node_id in enumerate(node_ids):
            self.nodes[node_id].pagerank = float(pr[i])

    def compute_hits(self, max_iterations: int = 100, tolerance: float = 1e-6) -> None:
        """
        Compute HITS (Hub and Authority) scores.

        - Authority: Nodes that are pointed to by many hubs (core modules)
        - Hub: Nodes that point to many authorities (aggregator/index files)

        Args:
            max_iterations: Maximum iterations.
            tolerance: Convergence tolerance.
        """
        n = len(self.nodes)
        if n == 0:
            return

        node_ids = list(self.nodes.keys())
        id_to_idx = {nid: i for i, nid in enumerate(node_ids)}

        # Initialize scores uniformly
        hub = np.ones(n)
        auth = np.ones(n)

        for iteration in range(max_iterations):
            # Update authority scores
            auth_new = np.zeros(n)
            for i, node_id in enumerate(node_ids):
                # Sum of hub scores of nodes pointing to this node
                sources = self.reverse_adjacency.get(node_id, set())
                for source_id in sources:
                    auth_new[i] += hub[id_to_idx[source_id]]

            # Update hub scores
            hub_new = np.zeros(n)
            for i, node_id in enumerate(node_ids):
                # Sum of authority scores of nodes this node points to
                targets = self.adjacency.get(node_id, set())
                for target_id in targets:
                    hub_new[i] += auth[id_to_idx[target_id]]

            # Normalize
            auth_norm = np.linalg.norm(auth_new)
            hub_norm = np.linalg.norm(hub_new)

            if auth_norm > 0:
                auth_new = auth_new / auth_norm
            if hub_norm > 0:
                hub_new = hub_new / hub_norm

            # Check convergence
            diff = np.abs(auth_new - auth).sum() + np.abs(hub_new - hub).sum()
            auth = auth_new
            hub = hub_new

            if diff < tolerance:
                logger.debug(f"HITS converged in {iteration + 1} iterations")
                break

        # Assign to nodes
        for i, node_id in enumerate(node_ids):
            self.nodes[node_id].authority_score = float(auth[i])
            self.nodes[node_id].hub_score = float(hub[i])

    def compute_betweenness(self) -> None:
        """
        Compute betweenness centrality for all nodes.

        Betweenness measures how often a node lies on shortest paths
        between other nodes. High betweenness = critical bridge.

        Uses Brandes' algorithm for efficiency.
        """
        n = len(self.nodes)
        if n == 0:
            return

        node_ids = list(self.nodes.keys())
        id_to_idx = {nid: i for i, nid in enumerate(node_ids)}

        betweenness = np.zeros(n)

        # Run BFS from each node
        for s_idx, s_id in enumerate(node_ids):
            # Single-source shortest paths
            stack = []
            pred: dict[int, list[int]] = {i: [] for i in range(n)}
            sigma = np.zeros(n)
            sigma[s_idx] = 1
            dist = np.full(n, -1)
            dist[s_idx] = 0

            queue = [s_idx]
            head = 0

            while head < len(queue):
                v = queue[head]
                head += 1
                stack.append(v)

                v_id = node_ids[v]
                for w_id in self.adjacency.get(v_id, set()):
                    w = id_to_idx[w_id]

                    if dist[w] < 0:
                        queue.append(w)
                        dist[w] = dist[v] + 1

                    if dist[w] == dist[v] + 1:
                        sigma[w] += sigma[v]
                        pred[w].append(v)

            # Accumulation
            delta = np.zeros(n)
            while stack:
                w = stack.pop()
                for v in pred[w]:
                    if sigma[w] > 0:
                        delta[v] += (sigma[v] / sigma[w]) * (1 + delta[w])
                if w != s_idx:
                    betweenness[w] += delta[w]

        # Normalize by (n-1)(n-2) for directed graph
        if n > 2:
            betweenness = betweenness / ((n - 1) * (n - 2))

        # Assign to nodes
        for i, node_id in enumerate(node_ids):
            self.nodes[node_id].betweenness = float(betweenness[i])

    def compute_clustering_coefficients(self) -> None:
        """
        Compute clustering coefficient for each node.

        For each node, counts triangles / possible triangles among neighbors.
        Uses undirected neighbor set (union of in + out).
        """
        for node_id in self.nodes:
            neighbors = self.adjacency.get(node_id, set()) | self.reverse_adjacency.get(node_id, set())
            k = len(neighbors)
            if k < 2:
                self.nodes[node_id].clustering_coeff = 0.0
                continue

            # Count edges between neighbors (in either direction)
            triangles = 0
            neighbor_list = list(neighbors)
            for i, n1 in enumerate(neighbor_list):
                for n2 in neighbor_list[i + 1:]:
                    if n2 in self.adjacency.get(n1, set()) or n1 in self.adjacency.get(n2, set()):
                        triangles += 1

            possible = k * (k - 1) / 2
            self.nodes[node_id].clustering_coeff = triangles / possible if possible > 0 else 0.0

    def compute_closeness(self, max_nodes: int = 1000) -> None:
        """
        Compute closeness centrality for each node via BFS.

        Closeness = (n-1) / sum_of_shortest_distances.
        Capped at max_nodes to avoid O(n^2) explosion on large graphs.

        Args:
            max_nodes: Skip computation if graph exceeds this size.
        """
        n = len(self.nodes)
        if n == 0 or n > max_nodes:
            return

        node_ids = list(self.nodes.keys())
        id_to_idx = {nid: i for i, nid in enumerate(node_ids)}

        for s_id in node_ids:
            # BFS from s_id
            dist = {s_id: 0}
            queue = [s_id]
            head = 0

            while head < len(queue):
                v = queue[head]
                head += 1
                for w in self.adjacency.get(v, set()):
                    if w not in dist:
                        dist[w] = dist[v] + 1
                        queue.append(w)

            # Closeness = (reachable-1) / sum_distances
            reachable = len(dist) - 1  # exclude self
            if reachable > 0:
                total_dist = sum(dist.values())
                self.nodes[s_id].closeness = reachable / total_dist if total_dist > 0 else 0.0
            else:
                self.nodes[s_id].closeness = 0.0

    def compute_community_embedding(self, dims: int = 2, max_nodes: int = 1000) -> None:
        """
        Compute 2D spectral community embedding using the normalized Laplacian.

        Processes each connected component separately to avoid degenerate
        eigenvectors from disconnected subgraphs. Uses the normalized
        Laplacian (L_norm = I - D^{-1/2} A D^{-1/2}) which is not biased
        by degree differences and produces clearer community separation.

        Args:
            dims: Number of embedding dimensions (default 2).
            max_nodes: Skip if graph exceeds this size.
        """
        n = len(self.nodes)
        if n < 3 or n > max_nodes:
            return

        node_ids = list(self.nodes.keys())
        id_to_idx = {nid: i for i, nid in enumerate(node_ids)}

        # Build symmetric adjacency matrix preserving direction info:
        # bidirectional edges get weight 1.0, unidirectional get 0.5
        A = np.zeros((n, n), dtype=np.float64)
        for src, targets in self.adjacency.items():
            i = id_to_idx[src]
            for tgt in targets:
                if tgt in id_to_idx:
                    j = id_to_idx[tgt]
                    A[i, j] += 0.5
                    A[j, i] += 0.5

        # Find connected components via BFS on the symmetric adjacency
        visited = np.zeros(n, dtype=bool)
        components: list[list[int]] = []

        for start in range(n):
            if visited[start]:
                continue
            component = []
            queue = [start]
            visited[start] = True
            head = 0
            while head < len(queue):
                v = queue[head]
                head += 1
                component.append(v)
                for w in range(n):
                    if not visited[w] and A[v, w] > 0:
                        visited[w] = True
                        queue.append(w)
            components.append(component)

        # Allocate output
        embedding = np.full((n, dims), 0.5, dtype=np.float64)
        num_components = len(components)

        for comp_idx, comp in enumerate(components):
            k = len(comp)

            # Each component maps to a sub-range of [0,1] so different
            # components occupy different regions of the embedding space.
            band_lo = comp_idx / num_components
            band_hi = (comp_idx + 1) / num_components

            if k < 3:
                # Small components: assign midpoint of their band
                mid = (band_lo + band_hi) / 2
                for node_local_idx in comp:
                    embedding[node_local_idx] = np.full(dims, mid)
                continue

            # Extract submatrix for this component
            idx = np.array(comp)
            A_sub = A[np.ix_(idx, idx)]

            # Normalized Laplacian: L_norm = I - D^{-1/2} A D^{-1/2}
            degrees = A_sub.sum(axis=1)
            D_inv_sqrt = np.zeros(k, dtype=np.float64)
            for i in range(k):
                if degrees[i] > 0:
                    D_inv_sqrt[i] = 1.0 / np.sqrt(degrees[i])

            D_inv_sqrt_mat = np.diag(D_inv_sqrt)
            L_norm = np.eye(k) - D_inv_sqrt_mat @ A_sub @ D_inv_sqrt_mat

            try:
                eigenvalues, eigenvectors = np.linalg.eigh(L_norm)
            except np.linalg.LinAlgError:
                continue

            if k < dims + 1:
                continue

            # Use 2nd and 3rd smallest eigenvectors (skip the constant 1st)
            sub_embedding = eigenvectors[:, 1:dims + 1]

            # Decorrelate: if dim0 and dim1 are highly correlated, replace dim1
            # with the next available eigenvector
            if dims >= 2 and k >= dims + 2:
                corr = np.corrcoef(sub_embedding[:, 0], sub_embedding[:, 1])[0, 1]
                if abs(corr) > 0.9:
                    sub_embedding[:, 1] = eigenvectors[:, dims + 1]

            # Normalize to component's band within [0, 1]
            band_width = band_hi - band_lo
            for d in range(dims):
                col = sub_embedding[:, d]
                col_min, col_max = col.min(), col.max()
                if col_max - col_min > 1e-10:
                    sub_embedding[:, d] = band_lo + ((col - col_min) / (col_max - col_min)) * band_width
                else:
                    sub_embedding[:, d] = (band_lo + band_hi) / 2

            # Write back
            for local_i, global_i in enumerate(comp):
                embedding[global_i] = sub_embedding[local_i]

        # Assign to nodes
        for i, node_id in enumerate(node_ids):
            self.nodes[node_id].community_embedding = embedding[i]

    def analyze(self, top_n: int = 10) -> GraphAnalysis:
        """
        Run full graph analysis.

        Args:
            top_n: Number of top nodes to return for each metric.

        Returns:
            GraphAnalysis with all computed metrics.
        """
        # Build graph if not already built
        if not self.nodes:
            self.build_graph()

        # Compute all metrics
        self.compute_pagerank()
        self.compute_hits()
        self.compute_betweenness()
        self.compute_clustering_coefficients()
        self.compute_closeness()
        self.compute_community_embedding()

        # Calculate summary metrics
        n = len(self.nodes)
        e = len(self.edges)

        total_in = sum(node.in_degree for node in self.nodes.values())
        total_out = sum(node.out_degree for node in self.nodes.values())

        avg_in = total_in / n if n > 0 else 0
        avg_out = total_out / n if n > 0 else 0
        density = e / (n * (n - 1)) if n > 1 else 0

        # Get top nodes by each metric
        nodes_list = list(self.nodes.values())

        top_pagerank = sorted(nodes_list, key=lambda x: x.pagerank, reverse=True)[:top_n]
        top_hubs = sorted(nodes_list, key=lambda x: x.hub_score, reverse=True)[:top_n]
        top_authorities = sorted(nodes_list, key=lambda x: x.authority_score, reverse=True)[:top_n]
        top_betweenness = sorted(nodes_list, key=lambda x: x.betweenness, reverse=True)[:top_n]

        return GraphAnalysis(
            nodes=nodes_list,
            edges=self.edges,
            total_nodes=n,
            total_edges=e,
            avg_in_degree=avg_in,
            avg_out_degree=avg_out,
            density=density,
            top_pagerank=[{"name": n.name, "score": n.pagerank, "path": n.file_path} for n in top_pagerank],
            top_hubs=[{"name": n.name, "score": n.hub_score, "path": n.file_path} for n in top_hubs],
            top_authorities=[{"name": n.name, "score": n.authority_score, "path": n.file_path} for n in top_authorities],
            top_betweenness=[{"name": n.name, "score": n.betweenness, "path": n.file_path} for n in top_betweenness],
        )

    def get_node_centrality(self, file_path: str) -> dict[str, Any] | None:
        """
        Get centrality metrics for a specific file.

        Args:
            file_path: Path to the file.

        Returns:
            Dictionary with centrality metrics or None if not found.
        """
        # Find node by path
        for node in self.nodes.values():
            if node.file_path == file_path or node.file_path.endswith(file_path):
                return {
                    "name": node.name,
                    "path": node.file_path,
                    "domain": node.domain,
                    "metrics": {
                        "pagerank": node.pagerank,
                        "hub_score": node.hub_score,
                        "authority_score": node.authority_score,
                        "betweenness": node.betweenness,
                        "in_degree": node.in_degree,
                        "out_degree": node.out_degree,
                    },
                    "interpretation": self._interpret_node(node),
                }
        return None

    def _interpret_node(self, node: GraphNode) -> list[str]:
        """Generate human-readable interpretation of node metrics."""
        interpretations = []

        # PageRank interpretation
        if node.pagerank > 0.1:
            interpretations.append("Critical module: Many important files depend on this")
        elif node.pagerank > 0.05:
            interpretations.append("Important module: Several files depend on this")

        # Hub/Authority interpretation
        if node.hub_score > 0.3:
            interpretations.append("Hub file: Aggregates many dependencies (e.g., index.js)")
        if node.authority_score > 0.3:
            interpretations.append("Authority: Core functionality that others depend on")

        # Betweenness interpretation
        if node.betweenness > 0.1:
            interpretations.append("Bridge: Critical path between modules - changes here propagate widely")

        # Degree interpretation
        if node.in_degree > 5:
            interpretations.append(f"High dependency: {node.in_degree} files depend on this")
        if node.out_degree > 10:
            interpretations.append(f"High coupling: Depends on {node.out_degree} other files")

        if node.in_degree == 0 and node.out_degree == 0:
            interpretations.append("Isolated: No detected dependencies (may be entry point or orphan)")
        elif node.in_degree == 0:
            interpretations.append("Leaf node: No files depend on this (consumer only)")
        elif node.out_degree == 0:
            interpretations.append("Root node: No dependencies (standalone utility)")

        return interpretations or ["Standard module with typical connectivity"]


def analyze_dependency_graph(conn: sqlite3.Connection, top_n: int = 10) -> dict[str, Any]:
    """
    Convenience function to analyze the dependency graph.

    Args:
        conn: Database connection.
        top_n: Number of top nodes to return.

    Returns:
        Analysis results as dictionary.
    """
    graph = DependencyGraph(conn)
    graph.build_graph()
    analysis = graph.analyze(top_n=top_n)
    return analysis.to_dict()


def get_file_centrality_score(conn: sqlite3.Connection, file_path: str) -> float:
    """Get normalized centrality score for a file (0.0-1.0).

    Combines PageRank and betweenness into a single score.
    Used by the hybrid risk calculator.

    Args:
        conn: Database connection.
        file_path: Path to the file.

    Returns:
        Normalized centrality score (0-1), where 1 = critical hub.
    """
    graph = DependencyGraph(conn)
    graph.build_graph()
    graph.compute_pagerank()
    graph.compute_betweenness()

    for node in graph.nodes.values():
        if node.file_path == file_path or node.file_path.endswith(file_path):
            # Combine PageRank (importance) and betweenness (bridge-ness)
            # PageRank is typically small (0-0.1), scale up
            pr_score = min(1.0, node.pagerank * 10.0)
            bt_score = min(1.0, node.betweenness * 5.0)
            return min(1.0, pr_score * 0.6 + bt_score * 0.4)

    return 0.0


def get_file_centrality(conn: sqlite3.Connection, file_path: str) -> dict[str, Any] | None:
    """
    Get centrality metrics for a specific file.

    Args:
        conn: Database connection.
        file_path: Path to the file.

    Returns:
        Centrality metrics or None if not found.
    """
    graph = DependencyGraph(conn)
    graph.build_graph()
    graph.compute_pagerank()
    graph.compute_hits()
    graph.compute_betweenness()
    return graph.get_node_centrality(file_path)

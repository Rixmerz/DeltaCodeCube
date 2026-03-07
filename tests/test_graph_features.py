"""Tests for graph features and graph extensions."""

import json
import sqlite3

import numpy as np
import pytest

from deltacodecube.cube.features.graph_features import GRAPH_DIMS, extract_graph_features
from deltacodecube.cube.graph import DependencyGraph, GraphNode


def _make_test_db():
    """Create an in-memory database with test data."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    # Create tables
    conn.executescript("""
        CREATE TABLE code_points (
            id TEXT PRIMARY KEY,
            file_path TEXT NOT NULL,
            function_name TEXT,
            lexical_features TEXT NOT NULL,
            structural_features TEXT NOT NULL,
            semantic_features TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            line_count INTEGER NOT NULL DEFAULT 0,
            dominant_domain TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE contracts (
            id TEXT PRIMARY KEY,
            caller_id TEXT NOT NULL,
            callee_id TEXT NOT NULL,
            contract_type TEXT NOT NULL,
            baseline_distance REAL NOT NULL,
            created_at TEXT
        );
    """)

    # Insert test nodes: A -> B -> C, A -> C (triangle)
    import json
    sem = json.dumps([0.2, 0.2, 0.2, 0.2, 0.2])
    lex = json.dumps([0.0] * 65)
    struct = json.dumps([0.0] * 16)

    for nid, path in [("a", "/a.py"), ("b", "/b.py"), ("c", "/c.py"), ("d", "/d.py")]:
        conn.execute(
            "INSERT INTO code_points VALUES (?, ?, NULL, ?, ?, ?, 'hash', 100, 'util', '2024-01-01', '2024-01-01')",
            (nid, path, lex, struct, sem),
        )

    # Edges: A->B, B->C, A->C (triangle among A,B,C), D is isolated
    conn.execute("INSERT INTO contracts VALUES ('ab', 'a', 'b', 'import', 0.5, '2024-01-01')")
    conn.execute("INSERT INTO contracts VALUES ('bc', 'b', 'c', 'import', 0.5, '2024-01-01')")
    conn.execute("INSERT INTO contracts VALUES ('ac', 'a', 'c', 'import', 0.5, '2024-01-01')")
    conn.commit()

    return conn


class TestGraphExtensions:
    def setup_method(self):
        self.conn = _make_test_db()
        self.graph = DependencyGraph(self.conn)
        self.graph.build_graph()

    def test_clustering_coefficients(self):
        self.graph.compute_clustering_coefficients()
        # A has 2 out-neighbors (B, C) and they have an edge between them
        # So A's clustering coeff should be 1.0 (1 triangle / 1 possible)
        assert self.graph.nodes["a"].clustering_coeff == 1.0
        # D has no neighbors
        assert self.graph.nodes["d"].clustering_coeff == 0.0

    def test_closeness(self):
        self.graph.compute_closeness()
        # A can reach B (1), C (1) -> closeness = 2/2 = 1.0
        assert self.graph.nodes["a"].closeness > 0
        # D can't reach anyone
        assert self.graph.nodes["d"].closeness == 0.0

    def test_community_embedding(self):
        self.graph.compute_community_embedding(dims=2)
        # Should assign 2D coordinates to each node
        for node in self.graph.nodes.values():
            assert len(node.community_embedding) == 2
            assert np.all(node.community_embedding >= 0)
            assert np.all(node.community_embedding <= 1)

    def test_full_analyze_includes_new_metrics(self):
        analysis = self.graph.analyze()
        for node_dict in analysis.to_dict()["nodes"]:
            assert "clustering_coeff" in node_dict
            assert "closeness" in node_dict


class TestGraphFeatures:
    def test_returns_zeros_without_graph(self):
        features = extract_graph_features("any_id", None)
        assert features.shape == (GRAPH_DIMS,)
        assert np.all(features == 0.0)

    def test_returns_zeros_for_unknown_node(self):
        conn = _make_test_db()
        graph = DependencyGraph(conn)
        graph.build_graph()
        features = extract_graph_features("nonexistent", graph)
        assert np.all(features == 0.0)

    def test_returns_features_for_known_node(self):
        conn = _make_test_db()
        graph = DependencyGraph(conn)
        graph.build_graph()
        graph.compute_pagerank()
        graph.compute_hits()
        graph.compute_betweenness()
        graph.compute_clustering_coefficients()
        graph.compute_closeness()
        graph.compute_community_embedding()

        features = extract_graph_features("a", graph)
        assert features.shape == (GRAPH_DIMS,)
        # Node A has edges, so some features should be non-zero
        assert features.sum() > 0

    def test_features_bounded(self):
        conn = _make_test_db()
        graph = DependencyGraph(conn)
        graph.build_graph()
        graph.compute_pagerank()
        graph.compute_hits()
        graph.compute_betweenness()
        graph.compute_clustering_coefficients()
        graph.compute_closeness()
        graph.compute_community_embedding()

        for node_id in graph.nodes:
            features = extract_graph_features(node_id, graph)
            assert np.all(features >= 0.0)
            assert np.all(features <= 1.0 + 1e-10)


class TestPreserveGraphOnReindex:
    """Test that _update_code_point(preserve_graph=True) keeps graph_features."""

    def _make_cube_db(self):
        """Create a DB with v2 schema for Cube tests."""
        from deltacodecube.db.schema import SCHEMA_SQL
        from deltacodecube.db.migrations import run_migrations
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA_SQL)
        run_migrations(conn)
        return conn

    def _make_cp(self, **overrides):
        """Create a minimal CodePoint for testing."""
        from deltacodecube.cube.code_point import CodePoint
        from datetime import datetime
        defaults = dict(
            id="cp1",
            file_path="/test.py",
            lexical=np.zeros(30),
            structural=np.zeros(16),
            semantic=np.array([0.2] * 5),
            content_hash="hash2",
            line_count=120,
            ast=np.zeros(20),
            graph_pos=np.zeros(10),
            patterns=np.zeros(10),
            feature_version=2,
            updated_at=datetime.now(),
        )
        defaults.update(overrides)
        return CodePoint(**defaults)

    def test_reindex_preserves_graph_features(self):
        """Graph features should not be overwritten when preserve_graph=True."""
        conn = self._make_cube_db()

        graph_values = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        lex = json.dumps([0.0] * 30)
        struct = json.dumps([0.0] * 16)
        sem = json.dumps([0.2] * 5)
        ast = json.dumps([0.0] * 20)
        graph = json.dumps(graph_values)
        patterns = json.dumps([0.0] * 10)

        conn.execute("""
            INSERT INTO code_points (id, file_path, lexical_features, structural_features,
                                      semantic_features, ast_features, graph_features,
                                      pattern_features, feature_version,
                                      content_hash, line_count, dominant_domain,
                                      created_at, updated_at)
            VALUES ('cp1', '/test.py', ?, ?, ?, ?, ?, ?, 2, 'hash1', 100, 'util',
                    '2024-01-01', '2024-01-01')
        """, (lex, struct, sem, ast, graph, patterns))
        conn.commit()

        from deltacodecube.cube.cube import DeltaCodeCube
        cube = DeltaCodeCube(conn)
        cp = self._make_cp(graph_pos=np.zeros(10))

        cube._update_code_point(cp, preserve_graph=True)

        row = conn.execute("SELECT graph_features FROM code_points WHERE id = 'cp1'").fetchone()
        stored_graph = json.loads(row["graph_features"])
        np.testing.assert_array_almost_equal(stored_graph, graph_values)

    def test_update_without_preserve_overwrites_graph(self):
        """Without preserve_graph, graph_features should be updated normally."""
        conn = self._make_cube_db()

        graph_values = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        lex = json.dumps([0.0] * 30)
        struct = json.dumps([0.0] * 16)
        sem = json.dumps([0.2] * 5)
        ast = json.dumps([0.0] * 20)
        graph = json.dumps(graph_values)
        patterns = json.dumps([0.0] * 10)

        conn.execute("""
            INSERT INTO code_points (id, file_path, lexical_features, structural_features,
                                      semantic_features, ast_features, graph_features,
                                      pattern_features, feature_version,
                                      content_hash, line_count, dominant_domain,
                                      created_at, updated_at)
            VALUES ('cp1', '/test.py', ?, ?, ?, ?, ?, ?, 2, 'hash1', 100, 'util',
                    '2024-01-01', '2024-01-01')
        """, (lex, struct, sem, ast, graph, patterns))
        conn.commit()

        from deltacodecube.cube.cube import DeltaCodeCube
        cube = DeltaCodeCube(conn)
        cp = self._make_cp(graph_pos=np.zeros(10))

        cube._update_code_point(cp, preserve_graph=False)

        row = conn.execute("SELECT graph_features FROM code_points WHERE id = 'cp1'").fetchone()
        stored_graph = json.loads(row["graph_features"])
        np.testing.assert_array_almost_equal(stored_graph, [0.0] * 10)


class TestCommunityEmbeddingSeparation:
    """Tests for the improved community embedding algorithm."""

    def _make_two_component_db(self):
        """Create a DB with two disjoint components: A->B->C and D->E->F."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row

        conn.executescript("""
            CREATE TABLE code_points (
                id TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                function_name TEXT,
                lexical_features TEXT NOT NULL,
                structural_features TEXT NOT NULL,
                semantic_features TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                line_count INTEGER NOT NULL DEFAULT 0,
                dominant_domain TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE contracts (
                id TEXT PRIMARY KEY,
                caller_id TEXT NOT NULL,
                callee_id TEXT NOT NULL,
                contract_type TEXT NOT NULL,
                baseline_distance REAL NOT NULL,
                created_at TEXT
            );
        """)

        import json
        sem = json.dumps([0.2, 0.2, 0.2, 0.2, 0.2])
        lex = json.dumps([0.0] * 65)
        struct = json.dumps([0.0] * 16)

        for nid, path in [
            ("a", "/a.py"), ("b", "/b.py"), ("c", "/c.py"),
            ("d", "/d.py"), ("e", "/e.py"), ("f", "/f.py"),
        ]:
            conn.execute(
                "INSERT INTO code_points VALUES (?, ?, NULL, ?, ?, ?, 'hash', 100, 'util', '2024-01-01', '2024-01-01')",
                (nid, path, lex, struct, sem),
            )

        # Component 1: A->B->C, A->C
        conn.execute("INSERT INTO contracts VALUES ('ab', 'a', 'b', 'import', 0.5, '2024-01-01')")
        conn.execute("INSERT INTO contracts VALUES ('bc', 'b', 'c', 'import', 0.5, '2024-01-01')")
        conn.execute("INSERT INTO contracts VALUES ('ac', 'a', 'c', 'import', 0.5, '2024-01-01')")
        # Component 2: D->E->F, D->F
        conn.execute("INSERT INTO contracts VALUES ('de', 'd', 'e', 'import', 0.5, '2024-01-01')")
        conn.execute("INSERT INTO contracts VALUES ('ef', 'e', 'f', 'import', 0.5, '2024-01-01')")
        conn.execute("INSERT INTO contracts VALUES ('df', 'd', 'f', 'import', 0.5, '2024-01-01')")
        conn.commit()
        return conn

    def test_community_embedding_separates_components(self):
        """Two disjoint components should get different embeddings."""
        conn = self._make_two_component_db()
        graph = DependencyGraph(conn)
        graph.build_graph()
        graph.compute_community_embedding(dims=2)

        # Get mean embedding per component
        comp1 = np.mean([graph.nodes[n].community_embedding for n in ["a", "b", "c"]], axis=0)
        comp2 = np.mean([graph.nodes[n].community_embedding for n in ["d", "e", "f"]], axis=0)

        # Components should have different mean embeddings
        diff = np.linalg.norm(comp1 - comp2)
        assert diff > 0.05, (
            f"Disjoint components should have different embeddings, "
            f"but diff={diff:.4f}. comp1={comp1}, comp2={comp2}"
        )

    def test_community_embedding_dims_decorrelated(self):
        """dim0 and dim1 should not be highly correlated after decorrelation fix."""
        conn = self._make_two_component_db()
        graph = DependencyGraph(conn)
        graph.build_graph()
        graph.compute_community_embedding(dims=2)

        embeddings = np.array([graph.nodes[n].community_embedding for n in graph.nodes])
        # Only check correlation if both dims have variance
        stds = embeddings.std(axis=0)
        if np.all(stds > 1e-10):
            corr = abs(np.corrcoef(embeddings[:, 0], embeddings[:, 1])[0, 1])
            assert corr < 0.95, (
                f"Community embedding dims should be decorrelated, "
                f"but abs(corr)={corr:.4f}"
            )

    def test_community_embedding_not_flat(self):
        """Embedding should have variance, not collapse to (0.5, 0.5)."""
        conn = _make_test_db()
        graph = DependencyGraph(conn)
        graph.build_graph()
        graph.compute_community_embedding(dims=2)

        embeddings = np.array([graph.nodes[n].community_embedding for n in graph.nodes])
        stds = embeddings.std(axis=0)

        # At least one dimension should have meaningful spread
        assert np.any(stds > 0.1), (
            f"Embedding too flat: std per dim = {stds}. "
            f"Expected at least one dim with std > 0.1"
        )

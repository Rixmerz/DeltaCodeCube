#!/usr/bin/env python3
"""Test script for DeltaCodeCube functionality."""

import sqlite3
from pathlib import Path

from bigcontext_mcp.db.schema import SCHEMA_SQL
from bigcontext_mcp.db.database import dict_factory
from bigcontext_mcp.cube import DeltaCodeCube, CodePoint
from bigcontext_mcp.cube.features import (
    extract_lexical_features,
    extract_structural_features,
    extract_semantic_features,
)


def test_feature_extractors():
    """Test feature extraction from code content."""
    print("Testing feature extractors...")

    test_code = '''
const express = require('express');
const router = express.Router();
const auth = require('../services/auth');

// Login endpoint
router.post('/login', async (req, res) => {
    try {
        const { email, password } = req.body;
        const token = await auth.validateUser(email, password);
        res.json({ token });
    } catch (error) {
        res.status(401).json({ error: error.message });
    }
});

module.exports = router;
'''

    # Test lexical features
    lexical = extract_lexical_features(test_code)
    print(f"  Lexical features: {lexical.shape} dims, norm={lexical.sum():.4f}")
    assert lexical.shape == (50,), f"Expected 50 dims, got {lexical.shape}"

    # Test structural features
    structural = extract_structural_features(test_code, ".js")
    print(f"  Structural features: {structural.shape} dims")
    print(f"    LOC: {structural[0]:.2f}, Functions: {structural[1]:.2f}, Imports: {structural[3]:.2f}")
    assert structural.shape == (8,), f"Expected 8 dims, got {structural.shape}"

    # Test semantic features
    semantic = extract_semantic_features(test_code)
    print(f"  Semantic features: {semantic.shape} dims")
    print(f"    auth: {semantic[0]:.2f}, api: {semantic[2]:.2f}")
    assert semantic.shape == (5,), f"Expected 5 dims, got {semantic.shape}"
    assert abs(semantic.sum() - 1.0) < 0.01, "Semantic features should sum to 1"

    print("  Feature extractors working!")


def test_code_point():
    """Test CodePoint creation and operations."""
    print("\nTesting CodePoint...")

    # Create test file
    test_file = Path("test-sample.ts")
    if not test_file.exists():
        test_file.write_text('''
interface User { id: string; name: string; }
class UserService {
    private users: Map<string, User>;
    constructor() { this.users = new Map(); }
    addUser(user: User): void { this.users.set(user.id, user); }
}
export { UserService };
''')

    from bigcontext_mcp.cube.code_point import create_code_point

    cp = create_code_point(str(test_file))

    print(f"  Created: {cp}")
    print(f"  Position: {cp.position.shape} dims")
    print(f"  Dominant domain: {cp.dominant_domain}")
    print(f"  Line count: {cp.line_count}")

    assert cp.position.shape == (63,), f"Expected 63 dims, got {cp.position.shape}"
    assert cp.line_count > 0, "Line count should be > 0"

    print("  CodePoint working!")


def test_cube():
    """Test DeltaCodeCube with in-memory database."""
    print("\nTesting DeltaCodeCube...")

    # Create in-memory database
    conn = sqlite3.connect(":memory:")
    conn.row_factory = dict_factory
    conn.executescript(SCHEMA_SQL)

    cube = DeltaCodeCube(conn)

    # Test indexing a file
    test_file = Path("test-sample.ts")
    cp = cube.index_file(str(test_file))
    print(f"  Indexed: {cp.file_path}")

    # Test get_position
    position = cube.get_position(str(test_file.resolve()))
    print(f"  Position retrieved: {position['dominant_domain']}")

    # Test stats
    stats = cube.get_stats()
    print(f"  Stats: {stats['total_files']} files, {stats['total_lines']} lines")

    assert stats["total_files"] == 1, "Should have 1 file indexed"

    # Test list
    code_points = cube.list_code_points()
    print(f"  Listed: {len(code_points)} code points")

    conn.close()
    print("  DeltaCodeCube working!")


def test_similarity():
    """Test similarity search."""
    print("\nTesting similarity search...")

    # Create in-memory database
    conn = sqlite3.connect(":memory:")
    conn.row_factory = dict_factory
    conn.executescript(SCHEMA_SQL)

    cube = DeltaCodeCube(conn)

    # Create multiple test files
    files = {
        "auth_service.js": '''
const jwt = require('jsonwebtoken');
async function validateToken(token) {
    return jwt.verify(token, process.env.SECRET);
}
async function login(email, password) {
    // Auth logic
}
module.exports = { validateToken, login };
''',
        "user_service.js": '''
const db = require('./database');
async function getUser(id) {
    return await db.query('SELECT * FROM users WHERE id = ?', [id]);
}
async function createUser(data) {
    return await db.insert('users', data);
}
module.exports = { getUser, createUser };
''',
        "api_routes.js": '''
const express = require('express');
const router = express.Router();
const auth = require('./auth_service');

router.get('/users/:id', async (req, res) => {
    const user = await getUser(req.params.id);
    res.json(user);
});
module.exports = router;
''',
    }

    # Index all files
    for name, content in files.items():
        path = Path(name)
        path.write_text(content)
        cube.index_file(str(path.resolve()))

    # Find similar to auth_service
    auth_path = Path("auth_service.js").resolve()
    similar = cube.find_similar(str(auth_path), limit=2)

    print(f"  Files similar to auth_service.js:")
    for s in similar:
        print(f"    - {Path(s['file_path']).name}: distance={s['distance']:.4f}, domain={s['dominant_domain']}")

    # Search by domain
    api_files = cube.search_by_domain("api")
    print(f"  API domain files: {len(api_files)}")

    # Cleanup
    for name in files:
        Path(name).unlink()

    conn.close()
    print("  Similarity search working!")


if __name__ == "__main__":
    print("=" * 60)
    print("DeltaCodeCube Test Suite")
    print("=" * 60)

    test_feature_extractors()
    test_code_point()
    test_cube()
    test_similarity()

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)

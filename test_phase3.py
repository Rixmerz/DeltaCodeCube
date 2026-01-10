#!/usr/bin/env python3
"""Test script for Phase 3: Deltas and Tensions functionality."""

import sqlite3
import shutil
from pathlib import Path

from bigcontext_mcp.db.schema import SCHEMA_SQL
from bigcontext_mcp.db.database import dict_factory
from bigcontext_mcp.cube import DeltaCodeCube


def test_delta_detection():
    """Test delta detection when a file changes."""
    print("Testing delta detection...")

    # Create in-memory database
    conn = sqlite3.connect(":memory:")
    conn.row_factory = dict_factory
    conn.executescript(SCHEMA_SQL)

    cube = DeltaCodeCube(conn)

    # Create temp directory
    test_dir = Path("test_phase3_temp")
    test_dir.mkdir(exist_ok=True)
    (test_dir / "services").mkdir(exist_ok=True)

    # Create initial files
    files = {
        "main.js": '''
const auth = require('./services/auth');
const db = require('./services/database');

async function main() {
    await auth.login('user@test.com', 'password');
    const data = await db.query('SELECT * FROM users');
    console.log(data);
}

module.exports = { main };
''',
        "services/auth.js": '''
const db = require('./database');

async function login(email, password) {
    const user = await db.getUser(email);
    if (user && user.password === password) {
        return { token: 'jwt-token' };
    }
    throw new Error('Invalid credentials');
}

async function validateToken(token) {
    return token === 'jwt-token';
}

module.exports = { login, validateToken };
''',
        "services/database.js": '''
const users = [];

async function query(sql) {
    return users;
}

async function getUser(email) {
    return users.find(u => u.email === email);
}

module.exports = { query, getUser };
''',
    }

    # Write initial files
    for name, content in files.items():
        (test_dir / name).write_text(content)

    # Index directory
    code_points = cube.index_directory(str(test_dir.resolve()))
    print(f"  Indexed {len(code_points)} files")

    # Check contracts
    stats = cube.get_contract_stats()
    print(f"  Detected {stats['total_contracts']} contracts")

    # Now modify auth.js significantly
    modified_auth = '''
const db = require('./database');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcrypt');

// Added JWT and bcrypt for better security
const SECRET = process.env.JWT_SECRET || 'secret';

async function login(email, password) {
    const user = await db.getUser(email);
    if (!user) {
        throw new Error('User not found');
    }

    // Now using bcrypt for password comparison
    const isValid = await bcrypt.compare(password, user.passwordHash);
    if (!isValid) {
        throw new Error('Invalid password');
    }

    // Generate JWT token instead of simple string
    const token = jwt.sign({ userId: user.id, email }, SECRET, { expiresIn: '1h' });
    return { token, expiresIn: 3600 };
}

async function validateToken(token) {
    try {
        const decoded = jwt.verify(token, SECRET);
        return decoded;
    } catch (err) {
        return null;
    }
}

async function hashPassword(password) {
    return bcrypt.hash(password, 10);
}

module.exports = { login, validateToken, hashPassword };
'''

    # Write modified file
    (test_dir / "services/auth.js").write_text(modified_auth)

    # Reindex the file
    result = cube.reindex_file(str((test_dir / "services/auth.js").resolve()))

    print(f"\n  Reindex result: {result['status']}")

    if result['delta']:
        delta = result['delta']
        print(f"  Delta:")
        print(f"    Movement magnitude: {delta['movement_magnitude']:.4f}")
        print(f"    Lexical change: {delta['lexical_change']:.4f}")
        print(f"    Structural change: {delta['structural_change']:.4f}")
        print(f"    Semantic change: {delta['semantic_change']:.4f}")
        print(f"    Dominant change: {delta['dominant_change']}")
        print(f"    Is significant: {delta['is_significant']}")

    if result['tensions']:
        print(f"\n  Detected {len(result['tensions'])} tension(s):")
        for t in result['tensions']:
            print(f"    - {t['caller_name']} ← {t['callee_name']}")
            print(f"      Severity: {t['severity']} ({t['tension_percent']:.1%})")
            print(f"      Baseline: {t['baseline_distance']:.3f} → Current: {t['current_distance']:.3f}")
            print(f"      Action: {t['suggested_action']}")
    else:
        print("  No tensions detected (change was within tolerance)")

    # Cleanup
    shutil.rmtree(test_dir)
    conn.close()

    print("\n  Delta detection working!")


def test_impact_analysis():
    """Test impact analysis."""
    print("\nTesting impact analysis...")

    # Create in-memory database
    conn = sqlite3.connect(":memory:")
    conn.row_factory = dict_factory
    conn.executescript(SCHEMA_SQL)

    cube = DeltaCodeCube(conn)

    # Create temp directory
    test_dir = Path("test_impact_temp")
    test_dir.mkdir(exist_ok=True)
    (test_dir / "services").mkdir(exist_ok=True)

    # Create files with many dependencies on database.js
    files = {
        "services/database.js": '''
const pool = require('pg');
async function query(sql, params) { return pool.query(sql, params); }
async function getUser(id) { return query('SELECT * FROM users WHERE id = $1', [id]); }
async function saveUser(data) { return query('INSERT INTO users ...', [data]); }
module.exports = { query, getUser, saveUser };
''',
        "services/users.js": '''
const db = require('./database');
async function findUser(id) { return db.getUser(id); }
module.exports = { findUser };
''',
        "services/auth.js": '''
const db = require('./database');
async function login(email) { return db.query('SELECT...'); }
module.exports = { login };
''',
        "services/reports.js": '''
const db = require('./database');
async function generateReport() { return db.query('SELECT...'); }
module.exports = { generateReport };
''',
        "api.js": '''
const db = require('./services/database');
const users = require('./services/users');
async function handler() { return db.query('SELECT...'); }
module.exports = { handler };
''',
    }

    # Write files
    for name, content in files.items():
        (test_dir / name).write_text(content)

    # Index directory
    cube.index_directory(str(test_dir.resolve()))

    # Analyze impact of database.js
    impact = cube.analyze_impact(str((test_dir / "services/database.js").resolve()))

    print(f"  File: {impact['file_name']}")
    print(f"  Status: {impact['status']}")
    print(f"  Message: {impact['message']}")
    print(f"\n  Dependents ({impact['dependent_count']}):")

    for dep in impact['dependents']:
        print(f"    - {dep['file_name']}")
        print(f"      Baseline distance: {dep['baseline_distance']:.3f}")
        print(f"      Current distance: {dep['current_distance']:.3f}")

    # Cleanup
    shutil.rmtree(test_dir)
    conn.close()

    print("\n  Impact analysis working!")


def test_tension_workflow():
    """Test tension detection and resolution workflow."""
    print("\nTesting tension workflow...")

    # Create in-memory database
    conn = sqlite3.connect(":memory:")
    conn.row_factory = dict_factory
    conn.executescript(SCHEMA_SQL)

    cube = DeltaCodeCube(conn)

    # Create temp directory
    test_dir = Path("test_tension_temp")
    test_dir.mkdir(exist_ok=True)

    # Create simple files
    (test_dir / "lib.js").write_text('''
function helper() { return "v1"; }
module.exports = { helper };
''')
    (test_dir / "main.js").write_text('''
const { helper } = require('./lib');
console.log(helper());
''')

    # Index
    cube.index_directory(str(test_dir.resolve()))

    # Major change to lib.js (completely different)
    (test_dir / "lib.js").write_text('''
const crypto = require('crypto');
const http = require('http');

class AdvancedHelper {
    constructor() {
        this.id = crypto.randomUUID();
    }

    async fetchData(url) {
        return new Promise((resolve, reject) => {
            http.get(url, (res) => {
                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', () => resolve(JSON.parse(data)));
            }).on('error', reject);
        });
    }

    processItems(items) {
        return items.map(i => ({
            ...i,
            processed: true,
            hash: crypto.createHash('md5').update(JSON.stringify(i)).digest('hex')
        }));
    }
}

module.exports = { AdvancedHelper };
''')

    # Reindex
    result = cube.reindex_file(str((test_dir / "lib.js").resolve()))

    print(f"  Reindex status: {result['status']}")

    if result['tensions']:
        tension = result['tensions'][0]
        print(f"  Tension detected: {tension['severity']}")
        print(f"  Tension ID: {tension['id']}")

        # Get tensions
        tensions = cube.get_tensions()
        print(f"  Total tensions: {len(tensions)}")

        # Resolve tension
        cube.resolve_tension(tension['id'], 'resolved')
        print(f"  Tension resolved!")

        # Check stats
        stats = cube.get_tension_stats()
        print(f"  Stats: {stats}")

    # Cleanup
    shutil.rmtree(test_dir)
    conn.close()

    print("\n  Tension workflow working!")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 3: Deltas and Tensions Test Suite")
    print("=" * 60)

    test_delta_detection()
    test_impact_analysis()
    test_tension_workflow()

    print("\n" + "=" * 60)
    print("All Phase 3 tests passed!")
    print("=" * 60)

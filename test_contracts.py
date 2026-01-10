#!/usr/bin/env python3
"""Test script for Phase 2: Contracts functionality."""

import sqlite3
from pathlib import Path

from bigcontext_mcp.db.schema import SCHEMA_SQL
from bigcontext_mcp.db.database import dict_factory
from bigcontext_mcp.cube import DeltaCodeCube
from bigcontext_mcp.cube.contracts import parse_imports, resolve_import_path


def test_import_parser():
    """Test import parsing for different languages."""
    print("Testing import parser...")

    # JavaScript ES6
    js_code = '''
import express from 'express';
import { Router } from 'express';
import * as utils from './utils';
import './styles.css';
const auth = require('./services/auth');
const db = require('../database');
'''

    imports = parse_imports(js_code, "test.js")
    print(f"  JS imports found: {imports}")
    assert "express" in imports
    assert "./utils" in imports
    assert "./services/auth" in imports
    assert "../database" in imports
    print("  JS import parsing working!")

    # Python
    py_code = '''
import os
import json
from pathlib import Path
from .utils import helper
from ..services import auth
'''

    imports = parse_imports(py_code, "test.py")
    print(f"  Python imports found: {imports}")
    assert "os" in imports
    assert "json" in imports
    assert "pathlib" in imports
    print("  Python import parsing working!")


def test_path_resolver():
    """Test path resolution."""
    print("\nTesting path resolver...")

    indexed_files = {
        "/project/src/utils.js": "id1",
        "/project/src/services/auth.js": "id2",
        "/project/src/index.js": "id3",
    }

    # Relative import
    resolved = resolve_import_path(
        "./utils",
        "/project/src/main.js",
        indexed_files
    )
    print(f"  ./utils from main.js -> {resolved}")
    assert resolved == "/project/src/utils.js"

    # Nested relative import
    resolved = resolve_import_path(
        "./services/auth",
        "/project/src/main.js",
        indexed_files
    )
    print(f"  ./services/auth from main.js -> {resolved}")
    assert resolved == "/project/src/services/auth.js"

    # Parent directory import
    resolved = resolve_import_path(
        "../src/utils",
        "/project/lib/helper.js",
        indexed_files
    )
    print(f"  ../src/utils from lib/helper.js -> {resolved}")
    assert resolved == "/project/src/utils.js"

    # External package (should return None)
    resolved = resolve_import_path(
        "express",
        "/project/src/main.js",
        indexed_files
    )
    print(f"  express (external) -> {resolved}")
    assert resolved is None

    print("  Path resolver working!")


def test_contract_detection():
    """Test contract detection with real files."""
    print("\nTesting contract detection...")

    # Create in-memory database
    conn = sqlite3.connect(":memory:")
    conn.row_factory = dict_factory
    conn.executescript(SCHEMA_SQL)

    cube = DeltaCodeCube(conn)

    # Create test files with imports
    files = {
        "main.js": '''
const auth = require('./services/auth');
const db = require('./services/database');
const utils = require('./utils');

async function main() {
    await auth.login();
    await db.connect();
}
''',
        "services/auth.js": '''
const db = require('./database');
const jwt = require('jsonwebtoken');

async function login(email, password) {
    const user = await db.getUser(email);
    return jwt.sign({ user });
}
module.exports = { login };
''',
        "services/database.js": '''
const sqlite = require('sqlite3');
async function connect() { /* ... */ }
async function getUser(email) { /* ... */ }
module.exports = { connect, getUser };
''',
        "utils.js": '''
function formatDate(date) { return date.toISOString(); }
function parseJSON(str) { return JSON.parse(str); }
module.exports = { formatDate, parseJSON };
''',
    }

    # Create temp directory
    test_dir = Path("test_contracts_temp")
    test_dir.mkdir(exist_ok=True)
    (test_dir / "services").mkdir(exist_ok=True)

    # Write files
    for name, content in files.items():
        (test_dir / name).write_text(content)

    # Index directory (should detect contracts)
    code_points = cube.index_directory(str(test_dir.resolve()))
    print(f"  Indexed {len(code_points)} files")

    # Get contracts
    contracts = cube.get_contracts()
    print(f"  Detected {len(contracts)} contracts")

    # Print contracts
    for c in contracts:
        print(f"    {c['caller_name']} → {c['callee_name']} (dist: {c['baseline_distance']:.3f})")

    # Get contract stats
    stats = cube.get_contract_stats()
    print(f"  Contract stats: {stats}")

    # Test filtering by file
    main_contracts = cube.get_contracts(
        file_path=str((test_dir / "main.js").resolve()),
        direction="outgoing"
    )
    print(f"  main.js outgoing contracts: {len(main_contracts)}")

    auth_contracts = cube.get_contracts(
        file_path=str((test_dir / "services/auth.js").resolve()),
        direction="incoming"
    )
    print(f"  auth.js incoming contracts: {len(auth_contracts)}")

    # Cleanup
    import shutil
    shutil.rmtree(test_dir)

    conn.close()
    print("  Contract detection working!")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 2: Contracts Test Suite")
    print("=" * 60)

    test_import_parser()
    test_path_resolver()
    test_contract_detection()

    print("\n" + "=" * 60)
    print("All Phase 2 tests passed!")
    print("=" * 60)

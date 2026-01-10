#!/usr/bin/env python3
"""Test script for code parser functionality."""

import sqlite3
from pathlib import Path

from bigcontext_mcp.parsers import detect_format, parse_code
from bigcontext_mcp.tools.ingest import ingest_document
from bigcontext_mcp.types import DocumentFormat


def test_code_parser():
    """Test the code parser directly."""
    print("Testing code parser...")

    # Test 1: Format detection
    test_file = Path("test-sample.ts")
    detected = detect_format(test_file)
    print(f"✓ Format detected: {detected}")
    assert detected == DocumentFormat.CODE, f"Expected CODE, got {detected}"

    # Test 2: Parse code file
    content, metadata = parse_code(test_file)
    print(f"✓ Parsed file: {len(content)} chars")
    print(f"  Metadata: {metadata}")
    assert "language" in metadata
    assert metadata["language"] == "typescript"

    # Test 3: Full ingestion
    print("\nTesting full ingestion...")
    from bigcontext_mcp.db.schema import SCHEMA_SQL
    from bigcontext_mcp.db.database import dict_factory

    conn = sqlite3.connect(":memory:")
    conn.row_factory = dict_factory
    conn.executescript(SCHEMA_SQL)

    result = ingest_document(
        conn,
        path=str(test_file.absolute()),
        title="Test TypeScript Sample",
        chunk_size=2000,
        overlap=100,
    )

    print(f"✓ Ingestion successful!")
    print(f"  Document ID: {result.document_id}")
    print(f"  Title: {result.title}")
    print(f"  Format: {result.format}")
    print(f"  Segments: {result.total_segments}")
    print(f"  Words: {result.total_words}")
    print(f"  Processing time: {result.processing_time_ms:.2f}ms")

    conn.close()

    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_code_parser()

"""Markdown parser."""

from pathlib import Path
from typing import Any

from bigcontext_mcp.parsers.base import BaseParser


class MdParser(BaseParser):
    """Parser for Markdown files."""

    def parse(self, file_path: Path) -> tuple[str, dict[str, Any]]:
        """Parse a Markdown file."""
        content = file_path.read_text(encoding="utf-8")

        # Extract title from first H1 if present
        title = None
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("# "):
                title = line[2:].strip()
                break

        return content, {
            "encoding": "utf-8",
            "original_path": str(file_path),
            "title": title,
        }

    def supported_extensions(self) -> list[str]:
        """Return supported extensions."""
        return [".md", ".markdown"]


def parse_md(file_path: Path | str) -> tuple[str, dict[str, Any]]:
    """Parse a Markdown file."""
    parser = MdParser()
    return parser.parse(Path(file_path))

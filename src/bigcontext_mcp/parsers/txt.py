"""Plain text parser."""

from pathlib import Path
from typing import Any

from bigcontext_mcp.parsers.base import BaseParser


class TxtParser(BaseParser):
    """Parser for plain text files."""

    def parse(self, file_path: Path) -> tuple[str, dict[str, Any]]:
        """Parse a plain text file."""
        content = file_path.read_text(encoding="utf-8")
        return content, {
            "encoding": "utf-8",
            "original_path": str(file_path),
        }

    def supported_extensions(self) -> list[str]:
        """Return supported extensions."""
        return [".txt", ".text"]


def parse_txt(file_path: Path | str) -> tuple[str, dict[str, Any]]:
    """Parse a plain text file."""
    parser = TxtParser()
    return parser.parse(Path(file_path))

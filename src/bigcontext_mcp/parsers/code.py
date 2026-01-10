"""Code file parser."""

from pathlib import Path
from typing import Any

from bigcontext_mcp.parsers.base import BaseParser


class CodeParser(BaseParser):
    """Parser for code files (JavaScript, TypeScript, etc)."""

    def parse(self, file_path: Path) -> tuple[str, dict[str, Any]]:
        """Parse a code file."""
        content = file_path.read_text(encoding="utf-8")

        # Calculate metadata
        line_count = content.count("\n") + 1
        extension = file_path.suffix

        return content, {
            "encoding": "utf-8",
            "original_path": str(file_path),
            "line_count": line_count,
            "extension": extension,
            "language": self._detect_language(extension),
        }

    def supported_extensions(self) -> list[str]:
        """Return supported extensions."""
        return [".ts", ".tsx", ".js", ".jsx"]

    def _detect_language(self, extension: str) -> str:
        """Detect programming language from extension."""
        language_map = {
            ".ts": "typescript",
            ".tsx": "typescript-react",
            ".js": "javascript",
            ".jsx": "javascript-react",
        }
        return language_map.get(extension.lower(), "unknown")


def parse_code(file_path: Path | str) -> tuple[str, dict[str, Any]]:
    """Parse a code file."""
    parser = CodeParser()
    return parser.parse(Path(file_path))

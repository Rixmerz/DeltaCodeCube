"""PDF parser using pdfplumber."""

from pathlib import Path
from typing import Any

import pdfplumber

from bigcontext_mcp.parsers.base import BaseParser


class PdfParser(BaseParser):
    """Parser for PDF files using pdfplumber."""

    def parse(self, file_path: Path) -> tuple[str, dict[str, Any]]:
        """Parse a PDF file."""
        content_parts = []
        page_count = 0
        metadata: dict[str, Any] = {}

        with pdfplumber.open(file_path) as pdf:
            page_count = len(pdf.pages)
            metadata = pdf.metadata or {}

            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    content_parts.append(text)

        content = "\n\n".join(content_parts)

        return content, {
            "original_path": str(file_path),
            "page_count": page_count,
            "info": metadata,
        }

    def supported_extensions(self) -> list[str]:
        """Return supported extensions."""
        return [".pdf"]


def parse_pdf(file_path: Path | str) -> tuple[str, dict[str, Any]]:
    """Parse a PDF file."""
    parser = PdfParser()
    return parser.parse(Path(file_path))

"""EPUB parser using ebooklib."""

from pathlib import Path
from typing import Any

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub

from bigcontext_mcp.parsers.base import BaseParser


class EpubParser(BaseParser):
    """Parser for EPUB files using ebooklib."""

    def parse(self, file_path: Path) -> tuple[str, dict[str, Any]]:
        """Parse an EPUB file."""
        book = epub.read_epub(str(file_path))

        # Extract metadata
        title = None
        title_items = book.get_metadata("DC", "title")
        if title_items:
            title = title_items[0][0]

        author = None
        author_items = book.get_metadata("DC", "creator")
        if author_items:
            author = author_items[0][0]

        # Extract content from all document items
        content_parts = []
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                # Parse HTML content
                soup = BeautifulSoup(item.get_content(), "lxml")

                # Remove script and style
                for element in soup(["script", "style"]):
                    element.decompose()

                text = soup.get_text().strip()
                if text:
                    content_parts.append(text)

        content = "\n\n".join(content_parts)

        return content, {
            "original_path": str(file_path),
            "title": title,
            "author": author,
            "item_count": len(content_parts),
        }

    def supported_extensions(self) -> list[str]:
        """Return supported extensions."""
        return [".epub"]


def parse_epub(file_path: Path | str) -> tuple[str, dict[str, Any]]:
    """Parse an EPUB file."""
    parser = EpubParser()
    return parser.parse(Path(file_path))

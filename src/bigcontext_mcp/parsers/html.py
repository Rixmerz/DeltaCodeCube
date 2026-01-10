"""HTML parser using BeautifulSoup."""

from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from bigcontext_mcp.parsers.base import BaseParser


class HtmlParser(BaseParser):
    """Parser for HTML files."""

    def parse(self, file_path: Path) -> tuple[str, dict[str, Any]]:
        """Parse an HTML file."""
        html_content = file_path.read_text(encoding="utf-8")
        soup = BeautifulSoup(html_content, "lxml")

        # Remove script and style elements
        for element in soup(["script", "style", "noscript"]):
            element.decompose()

        # Extract title
        title = None
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text().strip()

        # Extract main content - prefer article, main, or body
        content_element = soup.find("article")
        if not content_element:
            content_element = soup.find("main")
        if not content_element:
            content_element = soup.find("body")

        if not content_element:
            content_element = soup

        # Get text content, preserving structure
        content_parts = []
        for el in content_element.find_all(
            ["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "td", "th", "blockquote", "pre"]
        ):
            text = el.get_text().strip()
            if not text:
                continue

            tag_name = el.name
            # Add markdown-like headers for structure detection
            if tag_name.startswith("h") and len(tag_name) == 2 and tag_name[1].isdigit():
                level = int(tag_name[1])
                content_parts.append("#" * level + " " + text)
            else:
                content_parts.append(text)

        content = "\n\n".join(content_parts)
        if not content:
            content = soup.get_text().strip()

        return content, {
            "original_path": str(file_path),
            "title": title,
        }

    def supported_extensions(self) -> list[str]:
        """Return supported extensions."""
        return [".html", ".htm", ".xhtml"]


def parse_html(file_path: Path | str) -> tuple[str, dict[str, Any]]:
    """Parse an HTML file."""
    parser = HtmlParser()
    return parser.parse(Path(file_path))

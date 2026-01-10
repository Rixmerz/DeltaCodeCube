"""Document parsers for various formats."""

from pathlib import Path
from typing import Any

from bigcontext_mcp.parsers.code import CodeParser, parse_code
from bigcontext_mcp.parsers.epub import EpubParser, parse_epub
from bigcontext_mcp.parsers.html import HtmlParser, parse_html
from bigcontext_mcp.parsers.md import MdParser, parse_md
from bigcontext_mcp.parsers.pdf import PdfParser, parse_pdf
from bigcontext_mcp.parsers.txt import TxtParser, parse_txt
from bigcontext_mcp.types import DocumentFormat
from bigcontext_mcp.utils.errors import UnsupportedFormatError

__all__ = [
    "parse_document",
    "detect_format",
    "parse_txt",
    "parse_md",
    "parse_html",
    "parse_pdf",
    "parse_epub",
    "parse_code",
    "TxtParser",
    "MdParser",
    "HtmlParser",
    "PdfParser",
    "EpubParser",
    "CodeParser",
]

EXTENSION_TO_FORMAT: dict[str, DocumentFormat] = {
    ".txt": DocumentFormat.TXT,
    ".text": DocumentFormat.TXT,
    ".md": DocumentFormat.MD,
    ".markdown": DocumentFormat.MD,
    ".html": DocumentFormat.HTML,
    ".htm": DocumentFormat.HTML,
    ".xhtml": DocumentFormat.HTML,
    ".pdf": DocumentFormat.PDF,
    ".epub": DocumentFormat.EPUB,
    ".ts": DocumentFormat.CODE,
    ".tsx": DocumentFormat.CODE,
    ".js": DocumentFormat.CODE,
    ".jsx": DocumentFormat.CODE,
}


def detect_format(file_path: Path | str) -> DocumentFormat | None:
    """Detect document format from file extension."""
    path = Path(file_path)
    ext = path.suffix.lower()
    return EXTENSION_TO_FORMAT.get(ext)


def parse_document(
    file_path: Path | str,
    format: DocumentFormat | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    Parse a document and return its content and metadata.

    Args:
        file_path: Path to the document file.
        format: Optional format override. If not provided, will be detected.

    Returns:
        Tuple of (content, metadata)

    Raises:
        UnsupportedFormatError: If the format is not supported.
    """
    path = Path(file_path)
    detected_format = format or detect_format(path)

    if not detected_format:
        raise UnsupportedFormatError(path.suffix)

    match detected_format:
        case DocumentFormat.TXT:
            return parse_txt(path)
        case DocumentFormat.MD:
            return parse_md(path)
        case DocumentFormat.HTML:
            return parse_html(path)
        case DocumentFormat.PDF:
            return parse_pdf(path)
        case DocumentFormat.EPUB:
            return parse_epub(path)
        case DocumentFormat.CODE:
            return parse_code(path)
        case _:
            raise UnsupportedFormatError(str(detected_format))

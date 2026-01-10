"""Base parser interface."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseParser(ABC):
    """Abstract base class for document parsers."""

    @abstractmethod
    def parse(self, file_path: Path) -> tuple[str, dict[str, Any]]:
        """
        Parse a document and return its content and metadata.

        Args:
            file_path: Path to the document file.

        Returns:
            Tuple of (content, metadata)
        """
        pass

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions."""
        pass

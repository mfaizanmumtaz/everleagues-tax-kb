"""File Parser Service - LangChain-based text extraction from documents.

This module provides robust text extraction from various file formats using
LangChain document loaders as the primary extraction engine.

Supported formats:
- PDF (via PyMuPDFLoader)
- DOCX/DOC (via UnstructuredWordDocumentLoader)
- TXT (via TextLoader)
- XML (via UnstructuredXMLLoader)
- HTML/HTM (via BSHTMLLoader)
"""

from .service import FileParserService, get_file_parser_service
from .result import ParseResult
from .exceptions import (
    FileParserError,
    UnsupportedFileTypeError,
    ExtractionError,
    LoaderNotFoundError,
)

__all__ = [
    "FileParserService",
    "get_file_parser_service",
    "ParseResult",
    "FileParserError",
    "UnsupportedFileTypeError",
    "ExtractionError",
    "LoaderNotFoundError",
]

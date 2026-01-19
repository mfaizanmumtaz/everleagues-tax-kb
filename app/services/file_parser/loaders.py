"""LangChain loader configuration and mapping.

This module defines the mapping between file extensions and their
corresponding LangChain document loaders.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class LoaderConfig:
    """Configuration for a document loader."""

    loader_name: str
    package: str
    fallback_loader: Optional[str] = None
    fallback_package: Optional[str] = None
    requires_file_path: bool = True
    loader_kwargs: Dict[str, Any] = None
    install_hint: str = ""

    def __post_init__(self):
        if self.loader_kwargs is None:
            self.loader_kwargs = {}


# Primary LangChain loader mapping
# Key: file extension (lowercase with dot)
# Value: LoaderConfig with loader details
LOADER_MAPPING: Dict[str, LoaderConfig] = {
    # PDF files - PyMuPDFLoader for best quality
    ".pdf": LoaderConfig(
        loader_name="PyMuPDFLoader",
        package="langchain_community.document_loaders",
        fallback_loader="PDFPlumberLoader",
        fallback_package="langchain_community.document_loaders",
        requires_file_path=True,
        install_hint="pip install pymupdf",
    ),
    # Microsoft Word documents
    ".docx": LoaderConfig(
        loader_name="UnstructuredWordDocumentLoader",
        package="langchain_community.document_loaders",
        requires_file_path=True,
        install_hint="pip install unstructured python-docx",
    ),
    ".doc": LoaderConfig(
        loader_name="UnstructuredWordDocumentLoader",
        package="langchain_community.document_loaders",
        requires_file_path=True,
        install_hint="pip install unstructured python-docx antiword",
    ),
    # Plain text files
    ".txt": LoaderConfig(
        loader_name="TextLoader",
        package="langchain_community.document_loaders",
        requires_file_path=True,
        loader_kwargs={"autodetect_encoding": True},
    ),
    # XML files
    ".xml": LoaderConfig(
        loader_name="UnstructuredXMLLoader",
        package="langchain_community.document_loaders",
        requires_file_path=True,
        install_hint="pip install unstructured lxml",
    ),
    # HTML files
    ".html": LoaderConfig(
        loader_name="BSHTMLLoader",
        package="langchain_community.document_loaders",
        requires_file_path=True,
        install_hint="pip install beautifulsoup4 lxml",
    ),
    ".htm": LoaderConfig(
        loader_name="BSHTMLLoader",
        package="langchain_community.document_loaders",
        requires_file_path=True,
        install_hint="pip install beautifulsoup4 lxml",
    ),
}


def get_loader_config(extension: str) -> Optional[LoaderConfig]:
    """
    Get loader configuration for a file extension.

    Args:
        extension: File extension (with or without leading dot)

    Returns:
        LoaderConfig if extension is supported, None otherwise
    """
    # Normalize extension
    ext = extension.lower()
    if not ext.startswith("."):
        ext = f".{ext}"

    return LOADER_MAPPING.get(ext)


def get_supported_extensions() -> List[str]:
    """
    Get list of all supported file extensions.

    Returns:
        List of supported extensions (e.g., ['.pdf', '.docx', ...])
    """
    return list(LOADER_MAPPING.keys())


def is_supported(filename: str) -> bool:
    """
    Check if a filename has a supported extension.

    Args:
        filename: Filename to check

    Returns:
        True if file type is supported
    """
    import os

    _, ext = os.path.splitext(filename)
    return ext.lower() in LOADER_MAPPING


def get_loader_class(config: LoaderConfig, use_fallback: bool = False):
    """
    Dynamically import and return the loader class.

    Args:
        config: LoaderConfig with loader details
        use_fallback: If True and fallback exists, use fallback loader

    Returns:
        Loader class

    Raises:
        ImportError: If loader cannot be imported
    """
    import importlib

    if use_fallback and config.fallback_loader and config.fallback_package:
        loader_name = config.fallback_loader
        package = config.fallback_package
    else:
        loader_name = config.loader_name
        package = config.package

    try:
        module = importlib.import_module(package)
        loader_class = getattr(module, loader_name)
        return loader_class
    except (ImportError, AttributeError) as e:
        raise ImportError(
            f"Could not import {loader_name} from {package}. {config.install_hint}"
        ) from e


# MIME type to extension mapping for content-type based detection
MIME_TYPE_MAPPING: Dict[str, str] = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    "text/plain": ".txt",
    "text/xml": ".xml",
    "application/xml": ".xml",
    "text/html": ".html",
}


def get_extension_from_mime_type(mime_type: str) -> Optional[str]:
    """
    Get file extension from MIME type.

    Args:
        mime_type: MIME type string

    Returns:
        File extension or None if not recognized
    """
    return MIME_TYPE_MAPPING.get(mime_type.lower())

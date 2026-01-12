"""FileParserService - Main service for text extraction using LangChain loaders.

This service provides robust text extraction from various file formats using
LangChain document loaders as the primary extraction engine.
"""

import os
import time
import tempfile
from typing import List, Optional, Dict, Any, Type

from .result import ParseResult
from .exceptions import (
    FileParserError,
    UnsupportedFileTypeError,
    ExtractionError,
    LoaderNotFoundError,
)
from .loaders import (
    LOADER_MAPPING,
    LoaderConfig,
    get_loader_config,
    get_supported_extensions,
    is_supported,
    get_loader_class,
    get_extension_from_mime_type,
)


class FileParserService:
    """
    Robust file text extraction service using LangChain loaders.
    
    Primary extraction via LangChain document loaders:
    - PDF: PyMuPDFLoader (best for complex layouts)
    - DOCX/DOC: UnstructuredWordDocumentLoader
    - TXT: TextLoader (with encoding detection)
    - XML: UnstructuredXMLLoader
    - HTML: BSHTMLLoader
    
    Example usage:
        parser = get_file_parser_service()
        result = parser.extract_text(file_bytes, "document.pdf")
        
        if result.success:
            print(f"Extracted {result.word_count} words")
            print(result.text)
    """
    
    def __init__(self):
        """Initialize the FileParserService."""
        self._loader_cache: Dict[str, Type] = {}
        self._custom_loaders: Dict[str, LoaderConfig] = {}
    
    def extract_text(
        self,
        file_data: bytes,
        filename: str,
        use_fallback: bool = True,
        mime_type: Optional[str] = None,
    ) -> ParseResult:
        """
        Extract text from file bytes using LangChain loaders.
        
        This method writes the bytes to a temporary file and then uses
        the appropriate LangChain loader to extract text.
        
        Args:
            file_data: File content as bytes
            filename: Original filename (used to determine file type)
            use_fallback: If True, try fallback loader on failure
            mime_type: Optional MIME type for type detection
            
        Returns:
            ParseResult with extracted text and metadata
        """
        start_time = time.time()
        
        # Get file extension
        _, ext = os.path.splitext(filename)
        ext = ext.lower()
        
        # Try MIME type if extension is empty
        if not ext and mime_type:
            ext = get_extension_from_mime_type(mime_type) or ""
        
        if not ext:
            return ParseResult.empty(
                filename=filename,
                error="Could not determine file type from filename or MIME type"
            )
        
        # Check if file type is supported
        if not self._is_supported(ext):
            supported = self.get_supported_extensions()
            return ParseResult.empty(
                filename=filename,
                file_type=ext,
                error=f"Unsupported file type: {ext}. Supported: {', '.join(supported)}"
            )
        
        # Write bytes to temporary file
        temp_file = None
        try:
            # Create temp file with correct extension
            temp_file = tempfile.NamedTemporaryFile(
                suffix=ext,
                delete=False
            )
            temp_file.write(file_data)
            temp_file.close()
            
            # Extract using file path
            result = self.extract_text_from_path(
                file_path=temp_file.name,
                use_fallback=use_fallback,
                original_filename=filename,
            )
            
            # Update processing time
            processing_time = (time.time() - start_time) * 1000
            result.processing_time_ms = processing_time
            
            return result
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            return ParseResult(
                text="",
                success=False,
                file_type=ext,
                errors=[f"Extraction failed: {str(e)}"],
                processing_time_ms=processing_time,
                source_filename=filename,
            )
        finally:
            # Clean up temp file
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except Exception:
                    pass
    
    def extract_text_from_path(
        self,
        file_path: str,
        use_fallback: bool = True,
        original_filename: Optional[str] = None,
    ) -> ParseResult:
        """
        Extract text from a file path using LangChain loaders.
        
        This is the preferred method for large files as it avoids
        loading the entire file into memory.
        
        Args:
            file_path: Path to the file to extract
            use_fallback: If True, try fallback loader on failure
            original_filename: Original filename (if different from path)
            
        Returns:
            ParseResult with extracted text and metadata
        """
        start_time = time.time()
        
        # Get filename
        filename = original_filename or os.path.basename(file_path)
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        # Check file exists
        if not os.path.exists(file_path):
            return ParseResult.empty(
                filename=filename,
                file_type=ext,
                error=f"File not found: {file_path}"
            )
        
        # Check if file type is supported
        if not self._is_supported(ext):
            supported = self.get_supported_extensions()
            return ParseResult.empty(
                filename=filename,
                file_type=ext,
                error=f"Unsupported file type: {ext}. Supported: {', '.join(supported)}"
            )
        
        # Get loader config
        config = self._get_loader_config(ext)
        if not config:
            return ParseResult.empty(
                filename=filename,
                file_type=ext,
                error=f"No loader configured for {ext}"
            )
        
        # Try primary loader
        result = self._try_extraction(
            file_path=file_path,
            config=config,
            filename=filename,
            ext=ext,
            use_fallback=False,
        )
        
        # Try fallback if primary failed and fallback is available
        if not result.success and use_fallback and config.fallback_loader:
            fallback_result = self._try_extraction(
                file_path=file_path,
                config=config,
                filename=filename,
                ext=ext,
                use_fallback=True,
            )
            if fallback_result.success:
                result = fallback_result
        
        # Update processing time
        processing_time = (time.time() - start_time) * 1000
        result.processing_time_ms = processing_time
        
        return result
    
    def _try_extraction(
        self,
        file_path: str,
        config: LoaderConfig,
        filename: str,
        ext: str,
        use_fallback: bool = False,
    ) -> ParseResult:
        """
        Attempt text extraction with a specific loader.
        
        Args:
            file_path: Path to file
            config: Loader configuration
            filename: Original filename
            ext: File extension
            use_fallback: Whether to use fallback loader
            
        Returns:
            ParseResult
        """
        loader_name = config.fallback_loader if use_fallback else config.loader_name
        
        try:
            # Get loader class
            loader_class = self._get_cached_loader(config, use_fallback)
            
            # Prepare loader kwargs
            kwargs = dict(config.loader_kwargs) if config.loader_kwargs else {}
            
            # Create loader instance
            loader = loader_class(file_path, **kwargs)
            
            # Load documents
            documents = loader.load()
            
            # Convert to ParseResult
            return self._documents_to_result(
                documents=documents,
                filename=filename,
                file_type=ext,
                loader_name=loader_name,
            )
            
        except ImportError as e:
            return ParseResult(
                text="",
                success=False,
                file_type=ext,
                loader_used=loader_name,
                errors=[f"Loader import error: {str(e)}. {config.install_hint}"],
                source_filename=filename,
            )
        except Exception as e:
            return ParseResult(
                text="",
                success=False,
                file_type=ext,
                loader_used=loader_name,
                errors=[f"Extraction error with {loader_name}: {str(e)}"],
                source_filename=filename,
            )
    
    def _documents_to_result(
        self,
        documents: List[Any],
        filename: str,
        file_type: str,
        loader_name: str,
    ) -> ParseResult:
        """
        Convert LangChain Documents to ParseResult.
        
        Args:
            documents: List of LangChain Document objects
            filename: Original filename
            file_type: File extension
            loader_name: Name of loader used
            
        Returns:
            ParseResult
        """
        if not documents:
            return ParseResult(
                text="",
                success=True,  # Extraction succeeded but no content
                file_type=file_type,
                page_count=0,
                pages=[],
                loader_used=loader_name,
                parsing_quality=0.0,
                errors=["No content extracted from document"],
                source_filename=filename,
            )
        
        # Extract text from each document
        pages = []
        all_metadata = {}
        
        for doc in documents:
            page_content = doc.page_content if hasattr(doc, 'page_content') else str(doc)
            pages.append(page_content)
            
            # Merge metadata
            if hasattr(doc, 'metadata') and doc.metadata:
                all_metadata.update(doc.metadata)
        
        # Combine all text
        combined_text = "\n\n".join(pages)
        
        # Calculate quality score based on content
        quality = self._calculate_quality(combined_text, pages)
        
        return ParseResult(
            text=combined_text,
            success=True,
            file_type=file_type,
            page_count=len(pages),
            pages=pages,
            metadata=all_metadata,
            loader_used=loader_name,
            parsing_quality=quality,
            errors=[],
            source_filename=filename,
        )
    
    def _calculate_quality(self, text: str, pages: List[str]) -> float:
        """
        Calculate a quality score for the extracted text.
        
        Quality is based on:
        - Text length (not empty)
        - Readable characters ratio
        - Average page length consistency
        
        Args:
            text: Combined text
            pages: List of page texts
            
        Returns:
            Quality score from 0.0 to 1.0
        """
        if not text or not text.strip():
            return 0.0
        
        # Base score
        score = 1.0
        
        # Check for too many special characters (possible parsing issues)
        readable_chars = sum(1 for c in text if c.isalnum() or c.isspace())
        total_chars = len(text)
        
        if total_chars > 0:
            readable_ratio = readable_chars / total_chars
            if readable_ratio < 0.5:
                score *= 0.7  # Reduce score if too many special chars
        
        # Check for very short extraction (might be incomplete)
        if len(text) < 100:
            score *= 0.8
        
        # Check page consistency (if multiple pages)
        if len(pages) > 1:
            page_lengths = [len(p) for p in pages if p.strip()]
            if page_lengths:
                avg_length = sum(page_lengths) / len(page_lengths)
                # Check for empty or very short pages
                short_pages = sum(1 for l in page_lengths if l < avg_length * 0.1)
                if short_pages > len(page_lengths) * 0.3:
                    score *= 0.9  # Some pages might be poorly extracted
        
        return round(min(1.0, max(0.0, score)), 2)
    
    def _get_cached_loader(self, config: LoaderConfig, use_fallback: bool = False):
        """Get loader class from cache or import it."""
        cache_key = f"{config.loader_name}_{use_fallback}"
        
        if cache_key not in self._loader_cache:
            self._loader_cache[cache_key] = get_loader_class(config, use_fallback)
        
        return self._loader_cache[cache_key]
    
    def _get_loader_config(self, extension: str) -> Optional[LoaderConfig]:
        """Get loader config, checking custom loaders first."""
        ext = extension.lower()
        if not ext.startswith("."):
            ext = f".{ext}"
        
        # Check custom loaders first
        if ext in self._custom_loaders:
            return self._custom_loaders[ext]
        
        # Fall back to default mapping
        return get_loader_config(ext)
    
    def _is_supported(self, extension: str) -> bool:
        """Check if extension is supported."""
        ext = extension.lower()
        if not ext.startswith("."):
            ext = f".{ext}"
        
        return ext in self._custom_loaders or ext in LOADER_MAPPING
    
    def get_supported_extensions(self) -> List[str]:
        """
        Get list of all supported file extensions.
        
        Returns:
            List of supported extensions (e.g., ['.pdf', '.docx', ...])
        """
        extensions = set(get_supported_extensions())
        extensions.update(self._custom_loaders.keys())
        return sorted(list(extensions))
    
    def is_supported(self, filename: str) -> bool:
        """
        Check if a filename has a supported extension.
        
        Args:
            filename: Filename to check
            
        Returns:
            True if file type is supported
        """
        _, ext = os.path.splitext(filename)
        return self._is_supported(ext)
    
    def register_loader(
        self,
        extension: str,
        loader_name: str,
        package: str,
        fallback_loader: Optional[str] = None,
        fallback_package: Optional[str] = None,
        loader_kwargs: Optional[Dict[str, Any]] = None,
        install_hint: str = "",
    ) -> None:
        """
        Register a custom loader for a file extension.
        
        This allows extending the service with new file types or
        overriding default loaders.
        
        Args:
            extension: File extension (e.g., '.custom')
            loader_name: Name of the loader class
            package: Python package containing the loader
            fallback_loader: Optional fallback loader name
            fallback_package: Package for fallback loader
            loader_kwargs: Additional kwargs for the loader
            install_hint: Installation instructions
        """
        ext = extension.lower()
        if not ext.startswith("."):
            ext = f".{ext}"
        
        self._custom_loaders[ext] = LoaderConfig(
            loader_name=loader_name,
            package=package,
            fallback_loader=fallback_loader,
            fallback_package=fallback_package,
            loader_kwargs=loader_kwargs or {},
            install_hint=install_hint,
        )
        
        # Clear cache for this extension
        cache_keys = [k for k in self._loader_cache if ext in k]
        for key in cache_keys:
            del self._loader_cache[key]
    
    def unregister_loader(self, extension: str) -> bool:
        """
        Unregister a custom loader.
        
        Args:
            extension: File extension to unregister
            
        Returns:
            True if loader was unregistered, False if not found
        """
        ext = extension.lower()
        if not ext.startswith("."):
            ext = f".{ext}"
        
        if ext in self._custom_loaders:
            del self._custom_loaders[ext]
            return True
        return False


# Singleton instance
_file_parser_service: Optional[FileParserService] = None


def get_file_parser_service() -> FileParserService:
    """
    Get or create the FileParserService singleton.
    
    Returns:
        FileParserService instance
    """
    global _file_parser_service
    if _file_parser_service is None:
        _file_parser_service = FileParserService()
    return _file_parser_service

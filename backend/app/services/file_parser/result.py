"""ParseResult dataclass for file extraction results."""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class ParseResult:
    """
    Result of a file parsing operation.
    
    Contains extracted text, metadata, and processing information.
    Designed to provide comprehensive information about the extraction
    for downstream processing and quality assessment.
    
    Attributes:
        text: Combined text content from all pages/sections
        success: Whether the extraction completed successfully
        file_type: Detected file extension (e.g., '.pdf', '.docx')
        page_count: Number of pages/documents extracted
        pages: List of text content per page (for page-level access)
        metadata: Additional metadata from the document
        loader_used: Name of the LangChain loader used
        parsing_quality: Quality score from 0.0 to 1.0
        errors: List of any errors or warnings encountered
        processing_time_ms: Time taken to process in milliseconds
        char_count: Total character count of extracted text
        word_count: Total word count of extracted text
        source_filename: Original filename that was parsed
    """
    
    text: str
    success: bool
    file_type: str
    page_count: int = 0
    pages: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    loader_used: str = ""
    parsing_quality: float = 1.0
    errors: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    char_count: int = 0
    word_count: int = 0
    source_filename: str = ""
    
    def __post_init__(self):
        """Calculate char_count and word_count if not provided."""
        if self.text and self.char_count == 0:
            self.char_count = len(self.text)
        if self.text and self.word_count == 0:
            self.word_count = len(self.text.split())
    
    @property
    def is_empty(self) -> bool:
        """Check if the extracted text is empty or whitespace only."""
        return not self.text or not self.text.strip()
    
    @property
    def has_errors(self) -> bool:
        """Check if there were any errors during extraction."""
        return len(self.errors) > 0
    
    def get_page(self, index: int) -> Optional[str]:
        """
        Get text content for a specific page.
        
        Args:
            index: Zero-based page index
            
        Returns:
            Page text content or None if index is out of range
        """
        if 0 <= index < len(self.pages):
            return self.pages[index]
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ParseResult to dictionary for serialization."""
        return {
            "text": self.text,
            "success": self.success,
            "file_type": self.file_type,
            "page_count": self.page_count,
            "pages": self.pages,
            "metadata": self.metadata,
            "loader_used": self.loader_used,
            "parsing_quality": self.parsing_quality,
            "errors": self.errors,
            "processing_time_ms": self.processing_time_ms,
            "char_count": self.char_count,
            "word_count": self.word_count,
            "source_filename": self.source_filename,
            "is_empty": self.is_empty,
            "has_errors": self.has_errors,
        }
    
    @classmethod
    def empty(cls, filename: str = "", file_type: str = "", error: str = "") -> "ParseResult":
        """
        Create an empty ParseResult for failed extractions.
        
        Args:
            filename: Original filename
            file_type: File extension
            error: Error message to include
            
        Returns:
            ParseResult with empty text and success=False
        """
        errors = [error] if error else []
        return cls(
            text="",
            success=False,
            file_type=file_type,
            page_count=0,
            pages=[],
            metadata={},
            loader_used="",
            parsing_quality=0.0,
            errors=errors,
            processing_time_ms=0.0,
            char_count=0,
            word_count=0,
            source_filename=filename,
        )

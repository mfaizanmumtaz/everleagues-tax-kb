"""Text chunking service using LangChain RecursiveCharacterTextSplitter."""

from typing import List, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from ..models.chunk import ChunkCreate
from ..models.document import DocumentResponse


class TextChunker:
    """Service for splitting documents into chunks using LangChain."""

    def __init__(self):
        """Initialize text chunker with default settings."""
        # Default chunk size and overlap (in tokens)
        # Using token-based splitting for better model compatibility
        self.default_chunk_size = 600  # tokens (middle of 400-800 range)
        self.default_chunk_overlap = (
            100  # tokens (20% overlap for context preservation)
        )

        # Document type-specific chunk sizes (in tokens)
        self.chunk_sizes = {
            "irc": 600,  # IRC/CFR: 400-800 tokens
            "cfr": 600,
            "publication": 500,  # Pubs: section-based, slightly smaller
            "form": 400,  # Forms instructions: line groups
            "instructions": 400,
            "schedule": 400,
            "sales_tax": 450,  # Sales tax: 300-600 tokens
            "default": 600,
        }

        # Initialize the text splitter
        self._splitter = None

    def _get_splitter(
        self, chunk_size: int, chunk_overlap: int
    ) -> RecursiveCharacterTextSplitter:
        """Get or create text splitter with specified parameters."""
        # Use tiktoken encoder for token-based splitting (better for LLMs)
        # cl100k_base encoding works with GPT models
        return RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            encoding_name="cl100k_base",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            add_start_index=True,  # Track character index in original document
        )

    def _get_chunk_size_for_doc_type(self, doc_type: Optional[str]) -> int:
        """Get appropriate chunk size based on document type."""
        if not doc_type:
            return self.default_chunk_size

        doc_type_lower = doc_type.lower()

        # Check for specific document types
        for key, size in self.chunk_sizes.items():
            if key in doc_type_lower:
                return size

        return self.default_chunk_size

    def chunk_text(
        self,
        text: str,
        document_id: str,
        document: Optional[DocumentResponse] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> List[ChunkCreate]:
        """
        Split document text into chunks.

        Args:
            text: The full document text to split
            document_id: ID of the parent document
            document: Optional document metadata to denormalize into chunks
            chunk_size: Optional custom chunk size in tokens
            chunk_overlap: Optional custom chunk overlap in tokens

        Returns:
            List of ChunkCreate objects ready for indexing
        """
        if not text or not text.strip():
            return []

        # Determine chunk size based on document type
        if chunk_size is None:
            doc_type = document.doc_type if document else None
            chunk_size = self._get_chunk_size_for_doc_type(doc_type)

        if chunk_overlap is None:
            # Default to 20% overlap for context preservation
            chunk_overlap = max(50, int(chunk_size * 0.2))

        # Get text splitter
        splitter = self._get_splitter(chunk_size, chunk_overlap)

        # Split the text
        # split_text returns list of strings
        text_chunks = splitter.split_text(text)

        # Convert to ChunkCreate objects
        chunks = []
        for index, chunk_text in enumerate(text_chunks):
            # Extract metadata from document if available
            chunk = ChunkCreate(
                content=chunk_text.strip(),
                document_id=document_id,
                chunk_index=index,
                document_name=document.name if document else None,
                title=document.title if document else None,
                source_url=document.source_url if document else None,
                source_domain=document.source_domain if document else None,
                category=document.category if document else None,
                doc_type=document.doc_type if document else None,
                tax_year=document.tax_year if document else None,
                tax_type=document.tax_type if document else None,
                jurisdiction=document.jurisdiction if document else None,
                state=document.state if document else None,
                city=document.city if document else None,
                authority_level=document.authority_level if document else None,
                governance_state=document.governance_state if document else None,
                is_latest_for_tax_year=document.is_latest_for_tax_year
                if document
                else True,
            )
            chunks.append(chunk)

        return chunks

    def chunk_document(
        self,
        document: DocumentResponse,
        text: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> List[ChunkCreate]:
        """
        Split a document into chunks with full metadata.

        Args:
            document: DocumentResponse with metadata
            text: The full document text to split
            chunk_size: Optional custom chunk size in tokens
            chunk_overlap: Optional custom chunk overlap in tokens

        Returns:
            List of ChunkCreate objects ready for indexing
        """
        return self.chunk_text(
            text=text,
            document_id=document.id,
            document=document,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )


# Singleton instance
_chunker: Optional[TextChunker] = None


def get_text_chunker() -> TextChunker:
    """Get or create text chunker singleton."""
    global _chunker
    if _chunker is None:
        _chunker = TextChunker()
    return _chunker

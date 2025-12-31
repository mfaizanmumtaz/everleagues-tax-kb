"""Embedding service for generating vector embeddings."""

from typing import List, Optional
from ..config import settings


class EmbeddingService:
    """Service for generating embeddings using OpenAI."""
    
    def __init__(self, model: str = None, api_key: str = None):
        self.model = model or settings.embedding_model
        self.api_key = api_key or settings.openai_api_key
        self.dimension = settings.embedding_dimension
        self._client = None
    
    def _get_client(self):
        """Lazy load the OpenAI embeddings client."""
        if self._client is None:
            try:
                from langchain_openai import OpenAIEmbeddings
                self._client = OpenAIEmbeddings(
                    model=self.model,
                    openai_api_key=self.api_key
                )
            except ImportError:
                raise RuntimeError("langchain-openai is required for embedding generation")
            except Exception as e:
                raise RuntimeError(f"Failed to initialize embedding client: {e}")
        return self._client
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        client = self._get_client()
        embedding = client.embed_query(text)
        return embedding
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if not texts:
            return []
        
        # Filter out empty texts
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            raise ValueError("No valid texts provided")
        
        client = self._get_client()
        embeddings = client.embed_documents(valid_texts)
        return embeddings
    
    def validate_embedding(self, embedding: List[float]) -> bool:
        """Validate that an embedding has the correct dimension."""
        if not embedding:
            return False
        return len(embedding) == self.dimension


# Singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create embedding service singleton."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


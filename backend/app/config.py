"""Application configuration management."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache
from dotenv import load_dotenv,find_dotenv
load_dotenv(find_dotenv())

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Solr Configuration
    solr_base_url: str = "http://localhost:8983/solr"
    solr_username: Optional[str] = None
    solr_password: Optional[str] = None
    solr_documents_collection: str = "tax_documents"
    solr_chunks_collection: str = "tax_chunks"
    
    # Embedding Configuration
    openai_api_key: Optional[str] = None
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    
    # Hybrid Search Weights
    bm25_weight: float = 0.3  # alpha
    vector_weight: float = 0.5  # beta
    authority_weight: float = 0.4  # gamma
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api"
    debug: bool = False
    
    # CORS Configuration
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]
    
    # Pagination Defaults
    default_page_size: int = 20
    max_page_size: int = 100
    
    @property
    def solr_documents_url(self) -> str:
        """Get full URL for tax_documents collection."""
        return f"{self.solr_base_url}/{self.solr_documents_collection}"
    
    @property
    def solr_chunks_url(self) -> str:
        """Get full URL for tax_chunks collection."""
        return f"{self.solr_base_url}/{self.solr_chunks_collection}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


# Convenience function for direct import
settings = get_settings()


"""Application configuration management."""

from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ===========================================
    # Neo4j (Graph / Ontology) Configuration
    # ===========================================
    neo4j_uri: Optional[str] = None  # e.g. neo4j+s://xxxx.databases.neo4j.io
    neo4j_username: Optional[str] = None
    neo4j_password: Optional[str] = None
    neo4j_database: str = "neo4j"

    # Optional: list of OWL/RDF ontology URLs or paths for industry ontology import
    ontology_owl_urls: list[str] = []

    # ===========================================
    # PostgreSQL Database Configuration
    # ===========================================
    database_url: str = "postgresql://taxkb_user:password@localhost:5432/tax_kb"
    database_echo: bool = False  # SQL query logging
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # ===========================================
    # Solr Configuration
    # ===========================================
    solr_base_url: str = "http://localhost:8983/solr"
    solr_username: Optional[str] = None
    solr_password: Optional[str] = None
    solr_documents_collection: str = "tax_documents"
    solr_chunks_collection: str = "tax_chunks"

    # ===========================================
    # Azure Blob Storage Configuration
    # ===========================================
    azure_storage_connection_string: Optional[str] = None
    azure_storage_account_name: Optional[str] = None
    azure_storage_account_key: Optional[str] = None
    azure_container_raw: str = "raw-documents"
    azure_container_processed: str = "processed-documents"
    azure_container_uploads: str = "uploads"
    azure_container_api_pushed: str = "api-pushed"

    # ===========================================
    # Embedding Configuration
    # ===========================================
    openai_api_key: Optional[str] = None
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # ===========================================
    # LLM Configuration
    # ===========================================
    # Model for document classification (metadata extraction)
    classifier_llm_model: str = "gpt-4o-mini"
    classifier_llm_temperature: float = 0.1
    classifier_llm_max_tokens: int = 500
    
    # Model for RAG answer generation
    rag_llm_model: str = "gpt-4o-mini"
    rag_llm_temperature: float = 0.1
    rag_llm_max_tokens: int = 1500

    # ===========================================
    # Hybrid Search Weights
    # ===========================================
    bm25_weight: float = 0.3  # alpha
    vector_weight: float = 0.5  # beta
    authority_weight: float = 0.4  # gamma

    # ===========================================
    # API Configuration
    # ===========================================
    api_host: str = "0.0.0.0"
    api_port: int = 8001
    api_prefix: str = "/api"
    debug: bool = False

    # ===========================================
    # CORS Configuration
    # ===========================================
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000","https://eltaxdevsvcserver.everleagues.com"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    # ===========================================
    # Pagination Defaults
    # ===========================================
    default_page_size: int = 20
    max_page_size: int = 100

    # ===========================================
    # Scraper Configuration
    # ===========================================
    scraper_default_delay: float = 2.0
    scraper_default_rpm: int = 30
    scraper_default_timeout: int = 30
    scraper_max_files_per_session: int = 10000

    # ===========================================
    # File Upload Configuration
    # ===========================================
    max_upload_size_mb: int = 50
    allowed_file_extensions: list[str] = [
        ".pdf",
        ".doc",
        ".docx",
        ".txt",
        ".xml",
        ".html",
        ".htm",
    ]
    process_uploads_sync: bool = True  # Process immediately vs background

    # ===========================================
    # Celery / Queue Configuration
    # ===========================================
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    worker_concurrency: int = 4
    worker_max_retries: int = 3
    worker_retry_delay: int = 60
    scrape_task_soft_time_limit: int = 3600   # 1 hour soft limit for scrape tasks
    scrape_task_time_limit: int = 3660        # 1 hour + 1 min hard kill

    @property
    def max_upload_size_bytes(self) -> int:
        """Get maximum upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024

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

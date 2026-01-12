"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.routers import search, documents, dashboard, governance, urls, audit, upload
from app.services.solr_service import get_solr_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("Starting Tax KB API...")
    
    # Check PostgreSQL connection
    try:
        from sqlalchemy import text
        from app.database.connection import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print("  PostgreSQL: OK")
    except Exception as e:
        print(f"  PostgreSQL: NOT AVAILABLE ({e})")
    
    # Check Solr connection
    try:
        solr = get_solr_service()
        health = solr.health_check()
        if health.get("documents"):
            print("  Solr tax_documents: OK")
        else:
            print("  Solr tax_documents: NOT AVAILABLE")
        if health.get("chunks"):
            print("  Solr tax_chunks: OK")
        else:
            print("  Solr tax_chunks: NOT AVAILABLE")
    except Exception as e:
        print(f"  Solr connection error: {e}")
    
    # Check Azure Blob Storage
    try:
        from app.services.blob_storage_service import get_blob_storage_service
        blob_service = get_blob_storage_service()
        if blob_service.is_configured():
            print("  Azure Blob Storage: Configured")
        else:
            print("  Azure Blob Storage: NOT CONFIGURED")
    except Exception as e:
        print(f"  Azure Blob Storage: Error ({e})")
    
    print(f"API ready at http://{settings.api_host}:{settings.api_port}")
    
    yield
    
    # Shutdown
    print("Shutting down Tax KB API...")


# Create FastAPI app
app = FastAPI(
    title="Tax Knowledge Base API",
    description="""
    RESTful API for the Tax Knowledge Base system.
    
    ## Features
    
    - **Search**: Hybrid RAG search combining BM25, vector similarity, and authority weighting
    - **Documents**: CRUD operations for tax documents with governance workflows
    - **Dashboard**: System metrics and health monitoring
    - **Governance**: Audit logs and governance state management
    - **URLs**: Manage scraping sources
    
    ## Collections
    
    The API uses two Solr collections:
    - `tax_documents`: Document-level metadata and governance
    - `tax_chunks`: Chunk-level data with vectors for RAG search
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Include routers
app.include_router(search.router, prefix=settings.api_prefix)
app.include_router(documents.router, prefix=settings.api_prefix)
app.include_router(dashboard.router, prefix=settings.api_prefix)
app.include_router(governance.router, prefix=settings.api_prefix)
app.include_router(urls.router, prefix=settings.api_prefix)
app.include_router(audit.router, prefix=settings.api_prefix)
app.include_router(upload.router, prefix=settings.api_prefix)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Tax Knowledge Base API",
        "version": "1.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        solr = get_solr_service()
        health = solr.health_check()
        
        return {
            "status": "healthy" if all(health.values()) else "degraded",
            "solr_documents": health.get("documents", False),
            "solr_chunks": health.get("chunks", False),
            "version": "1.0.0",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "solr_documents": False,
            "solr_chunks": False,
            "version": "1.0.0",
            "error": str(e),
        }


# For running with uvicorn directly
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )


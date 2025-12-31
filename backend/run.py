"""Script to run the FastAPI server."""

import uvicorn
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    from app.config import settings
    
    print("=" * 50)
    print("Tax Knowledge Base API")
    print("=" * 50)
    print(f"Solr URL: {settings.solr_base_url}")
    print(f"Documents Collection: {settings.solr_documents_collection}")
    print(f"Chunks Collection: {settings.solr_chunks_collection}")
    print("=" * 50)
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )


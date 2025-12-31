"""Solr service wrapper using requests module."""

import requests
import json
from typing import Optional, List, Dict, Any, Tuple
from ..config import settings


class SolrException(Exception):
    """Custom exception for Solr errors."""
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class SolrService:
    """Wrapper for Solr operations using requests module."""
    
    def __init__(
        self,
        base_url: str = None,
        documents_collection: str = None,
        chunks_collection: str = None,
        timeout: int = 30,
        username: str = None,
        password: str = None
    ):
        self.base_url = base_url or settings.solr_base_url
        self.documents_collection = documents_collection or settings.solr_documents_collection
        self.chunks_collection = chunks_collection or settings.solr_chunks_collection
        self.timeout = timeout
        self.username = username or settings.solr_username
        self.password = password or settings.solr_password

        self.documents_url = f"{self.base_url}/{self.documents_collection}"
        self.chunks_url = f"{self.base_url}/{self.chunks_collection}"
    
    def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Any] = None,
        json_data: Optional[Any] = None
    ) -> Dict:
        """Make HTTP request to Solr."""
        try:
            # Prepare authentication if credentials are provided
            auth = None
            if self.username and self.password:
                auth = (self.username, self.password)

            response = requests.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json_data,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
                auth=auth
            )
            
            result = response.json()
            
            if response.status_code >= 400:
                error_msg = result.get("error", {}).get("msg", "Unknown Solr error")
                raise SolrException(
                    message=error_msg,
                    status_code=response.status_code,
                    details=result.get("error", {})
                )
            
            return result
            
        except requests.exceptions.Timeout:
            raise SolrException("Solr request timed out", status_code=504)
        except requests.exceptions.ConnectionError:
            raise SolrException("Could not connect to Solr", status_code=503)
        except json.JSONDecodeError:
            raise SolrException("Invalid JSON response from Solr", status_code=500)
    
    # ==================== Health Check ====================
    
    def ping(self, collection: str) -> bool:
        """Check if a collection is available."""
        try:
            url = f"{self.base_url}/{collection}/admin/ping"
            result = self._make_request("GET", url, params={"wt": "json"})
            return result.get("status") == "OK"
        except Exception:
            return False
    
    def health_check(self) -> Dict[str, bool]:
        """Check health of both collections."""
        return {
            "documents": self.ping(self.documents_collection),
            "chunks": self.ping(self.chunks_collection)
        }
    
    # ==================== Document Operations ====================
    
    def get_document(self, doc_id: str) -> Optional[Dict]:
        """Get a document by ID."""
        url = f"{self.documents_url}/select"
        params = {
            "q": f"id:{doc_id}",
            "wt": "json",
            "rows": 1
        }
        result = self._make_request("GET", url, params=params)
        docs = result.get("response", {}).get("docs", [])
        return docs[0] if docs else None
    
    def search_documents(
        self,
        query: str = "*:*",
        filters: Optional[List[str]] = None,
        fields: Optional[List[str]] = None,
        sort: str = "id asc",
        start: int = 0,
        rows: int = 20
    ) -> Tuple[List[Dict], int]:
        """Search documents with filters."""
        url = f"{self.documents_url}/select"
        params = {
            "q": query,
            "wt": "json",
            "start": start,
            "rows": rows,
            "sort": sort
        }
        
        if filters:
            params["fq"] = filters
        
        if fields:
            params["fl"] = ",".join(fields)
        
        result = self._make_request("GET", url, params=params)
        response = result.get("response", {})
        return response.get("docs", []), response.get("numFound", 0)
    
    def create_document(self, doc: Dict) -> bool:
        """Create a new document."""
        url = f"{self.documents_url}/update"
        params = {"commit": "true", "wt": "json"}
        result = self._make_request("POST", url, params=params, json_data=[doc])
        return result.get("responseHeader", {}).get("status") == 0
    
    def update_document(self, doc_id: str, updates: Dict) -> bool:
        """Update an existing document."""
        # Solr atomic update format
        update_doc = {"id": doc_id}
        for key, value in updates.items():
            if key != "id":
                update_doc[key] = {"set": value}
        
        url = f"{self.documents_url}/update"
        params = {"commit": "true", "wt": "json"}
        result = self._make_request("POST", url, params=params, json_data=[update_doc])
        return result.get("responseHeader", {}).get("status") == 0
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document by ID."""
        url = f"{self.documents_url}/update"
        params = {"commit": "true", "wt": "json"}
        delete_cmd = {"delete": {"id": doc_id}}
        result = self._make_request("POST", url, params=params, json_data=delete_cmd)
        return result.get("responseHeader", {}).get("status") == 0
    
    def delete_documents_by_query(self, query: str) -> bool:
        """Delete documents matching a query."""
        url = f"{self.documents_url}/update"
        params = {"commit": "true", "wt": "json"}
        delete_cmd = {"delete": {"query": query}}
        result = self._make_request("POST", url, params=params, json_data=delete_cmd)
        return result.get("responseHeader", {}).get("status") == 0
    
    # ==================== Chunk Operations ====================
    
    def get_chunk(self, chunk_id: str) -> Optional[Dict]:
        """Get a chunk by ID."""
        url = f"{self.chunks_url}/select"
        params = {
            "q": f"id:{chunk_id}",
            "wt": "json",
            "rows": 1
        }
        result = self._make_request("GET", url, params=params)
        docs = result.get("response", {}).get("docs", [])
        return docs[0] if docs else None
    
    def search_chunks(
        self,
        query: str = "*:*",
        filters: Optional[List[str]] = None,
        fields: Optional[List[str]] = None,
        sort: str = "id asc",
        start: int = 0,
        rows: int = 20
    ) -> Tuple[List[Dict], int]:
        """Search chunks with filters."""
        url = f"{self.chunks_url}/select"
        params = {
            "q": query,
            "wt": "json",
            "start": start,
            "rows": rows,
            "sort": sort
        }
        
        if filters:
            params["fq"] = filters
        
        if fields:
            params["fl"] = ",".join(fields)
        
        result = self._make_request("GET", url, params=params)
        response = result.get("response", {})
        return response.get("docs", []), response.get("numFound", 0)
    
    def get_chunks_by_document(
        self,
        document_id: str,
        start: int = 0,
        rows: int = 100
    ) -> Tuple[List[Dict], int]:
        """Get all chunks for a document."""
        return self.search_chunks(
            query="*:*",
            filters=[f"documentId:{document_id}"],
            sort="chunkIndex asc",
            start=start,
            rows=rows
        )
    
    def create_chunk(self, chunk: Dict) -> bool:
        """Create a new chunk."""
        url = f"{self.chunks_url}/update"
        params = {"commit": "true", "wt": "json"}
        result = self._make_request("POST", url, params=params, json_data=[chunk])
        return result.get("responseHeader", {}).get("status") == 0
    
    def create_chunks_bulk(self, chunks: List[Dict]) -> bool:
        """Create multiple chunks in bulk."""
        if not chunks:
            return True
        
        url = f"{self.chunks_url}/update"
        params = {"commit": "true", "wt": "json"}
        result = self._make_request("POST", url, params=params, json_data=chunks)
        return result.get("responseHeader", {}).get("status") == 0
    
    def update_chunk(self, chunk_id: str, updates: Dict) -> bool:
        """Update an existing chunk."""
        update_doc = {"id": chunk_id}
        for key, value in updates.items():
            if key != "id":
                update_doc[key] = {"set": value}
        
        url = f"{self.chunks_url}/update"
        params = {"commit": "true", "wt": "json"}
        result = self._make_request("POST", url, params=params, json_data=[update_doc])
        return result.get("responseHeader", {}).get("status") == 0
    
    def delete_chunk(self, chunk_id: str) -> bool:
        """Delete a chunk by ID."""
        url = f"{self.chunks_url}/update"
        params = {"commit": "true", "wt": "json"}
        delete_cmd = {"delete": {"id": chunk_id}}
        result = self._make_request("POST", url, params=params, json_data=delete_cmd)
        return result.get("responseHeader", {}).get("status") == 0
    
    def delete_chunks_by_document(self, document_id: str) -> bool:
        """Delete all chunks for a document."""
        url = f"{self.chunks_url}/update"
        params = {"commit": "true", "wt": "json"}
        delete_cmd = {"delete": {"query": f"documentId:{document_id}"}}
        result = self._make_request("POST", url, params=params, json_data=delete_cmd)
        return result.get("responseHeader", {}).get("status") == 0
    
    # ==================== Vector Search ====================
    
    def vector_search(
        self,
        vector: List[float],
        top_k: int = 10,
        filters: Optional[List[str]] = None,
        fields: Optional[List[str]] = None
    ) -> List[Dict]:
        """Perform KNN vector search on chunks."""
        url = f"{self.chunks_url}/select"
        
        # Format vector as string for Solr
        vector_str = "[" + ",".join(str(v) for v in vector) + "]"
        
        # Build the query data - use POST to avoid URI too long error
        # The vector string is very long (1536 dimensions) and exceeds URL limits
        data = {
            "q": f"{{!knn f=vector topK={top_k}}}{vector_str}",
            "wt": "json",
            "rows": top_k
        }
        
        if filters:
            data["fq"] = filters
        
        if fields:
            data["fl"] = ",".join(fields) + ",score"
        else:
            data["fl"] = "*,score"
        
        # Use POST with form data for vector search (URL would be too long for GET)
        try:
            # Prepare authentication if credentials are provided
            auth = None
            if self.username and self.password:
                auth = (self.username, self.password)

            response = requests.post(
                url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=self.timeout,
                auth=auth
            )
            
            result = response.json()
            
            if response.status_code >= 400:
                error_msg = result.get("error", {}).get("msg", "Unknown Solr error")
                raise SolrException(
                    message=error_msg,
                    status_code=response.status_code,
                    details=result.get("error", {})
                )
            
            return result.get("response", {}).get("docs", [])
            
        except requests.exceptions.Timeout:
            raise SolrException("Solr vector search timed out", status_code=504)
        except requests.exceptions.ConnectionError:
            raise SolrException("Could not connect to Solr", status_code=503)
        except json.JSONDecodeError:
            raise SolrException("Invalid JSON response from Solr vector search", status_code=500)
    
    def bm25_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[List[str]] = None,
        fields: Optional[List[str]] = None
    ) -> List[Dict]:
        """Perform BM25 text search on chunks."""
        url = f"{self.chunks_url}/select"
        
        params = {
            "q": query,
            "defType": "edismax",
            "qf": "content^2 documentName title",
            "wt": "json",
            "rows": top_k
        }
        
        if filters:
            params["fq"] = filters
        
        if fields:
            params["fl"] = ",".join(fields) + ",score"
        else:
            params["fl"] = "*,score"
        
        result = self._make_request("GET", url, params=params)
        return result.get("response", {}).get("docs", [])
    
    # ==================== Aggregations ====================
    
    def get_document_stats(self) -> Dict[str, Any]:
        """Get statistics about documents collection."""
        url = f"{self.documents_url}/select"
        params = {
            "q": "*:*",
            "wt": "json",
            "rows": 0,
            "facet": "true",
            "facet.field": ["governanceState", "syncStatus", "indexStatus", "jurisdiction"],
            "stats": "true",
            "stats.field": ["chunkCount", "tokensIndexed"]
        }
        
        result = self._make_request("GET", url, params=params)
        
        return {
            "total": result.get("response", {}).get("numFound", 0),
            "facets": result.get("facet_counts", {}).get("facet_fields", {}),
            "stats": result.get("stats", {}).get("stats_fields", {})
        }
    
    def get_chunk_stats(self) -> Dict[str, Any]:
        """Get statistics about chunks collection."""
        url = f"{self.chunks_url}/select"
        params = {
            "q": "*:*",
            "wt": "json",
            "rows": 0,
            "facet": "true",
            "facet.field": ["jurisdiction", "governanceState", "taxYear"],
            "stats": "true",
            "stats.field": ["tokenCount", "charCount"]
        }
        
        result = self._make_request("GET", url, params=params)
        
        return {
            "total": result.get("response", {}).get("numFound", 0),
            "facets": result.get("facet_counts", {}).get("facet_fields", {}),
            "stats": result.get("stats", {}).get("stats_fields", {})
        }


# Singleton instance
_solr_service: Optional[SolrService] = None


def get_solr_service() -> SolrService:
    """Get or create Solr service singleton."""
    global _solr_service
    if _solr_service is None:
        _solr_service = SolrService()
    return _solr_service


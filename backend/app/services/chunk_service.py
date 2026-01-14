"""Chunk service for chunk operations."""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from ..config import settings
from ..models.chunk import ChunkCreate, ChunkUpdate, ChunkResponse, BulkChunkCreate, BulkChunkResponse
from ..models.common import FilterParams
from .solr_service import get_solr_service, SolrService
from .embedding_service import get_embedding_service, EmbeddingService


class ChunkService:
    """Service for chunk CRUD operations."""
    
    def __init__(
        self,
        solr_service: SolrService = None,
        embedding_service: EmbeddingService = None
    ):
        self.solr = solr_service or get_solr_service()
        self.embeddings = embedding_service or get_embedding_service()
    
    def _build_filters(self, filters: Optional[FilterParams]) -> List[str]:
        """Build Solr filter queries from FilterParams."""
        fq = []
        
        if not filters:
            return fq
        
        if filters.jurisdiction:
            fq.append(f"jurisdiction:{filters.jurisdiction}")
        
        if filters.state:
            fq.append(f"state:{filters.state}")
        
        if filters.tax_year:
            fq.append(f"taxYear:{filters.tax_year}")
        
        if filters.category:
            categories = " OR ".join(filters.category)
            fq.append(f"category:({categories})")
        
        if filters.authority_level:
            fq.append(f"authorityLevel:{filters.authority_level}")
        
        if filters.governance_state:
            fq.append(f"governanceState:\"{filters.governance_state.value}\"")
        
        if filters.is_latest_for_tax_year is not None:
            fq.append(f"isLatestForTaxYear:{str(filters.is_latest_for_tax_year).lower()}")
        
        return fq
    
    def _solr_to_response(self, doc: Dict) -> ChunkResponse:
        """Convert Solr document to ChunkResponse model."""
        return ChunkResponse(
            id=doc.get("id", ""),
            chunk_id=doc.get("chunkId", doc.get("id", "")),
            content=doc.get("content", ""),
            document_id=doc.get("documentId", ""),
            chunk_index=doc.get("chunkIndex", 0),
            
            # Denormalized fields
            document_name=doc.get("documentName"),
            title=doc.get("title"),
            source_url=doc.get("sourceUrl"),
            source_domain=doc.get("sourceDomain"),
            category=doc.get("category"),
            doc_type=doc.get("docType"),
            
            # Tax fields
            tax_year=doc.get("taxYear"),
            tax_type=doc.get("taxType"),
            jurisdiction=doc.get("jurisdiction"),
            state=doc.get("state"),
            city=doc.get("city"),
            authority_level=doc.get("authorityLevel"),
            
            # Governance
            governance_state=doc.get("governanceState"),
            is_latest_for_tax_year=doc.get("isLatestForTaxYear", True),
            
            # Vector
            vector=doc.get("vector"),
            
            # Metadata
            paragraph_number=doc.get("paragraphNumber"),
            section_title=doc.get("sectionTitle"),
            page_number=doc.get("pageNumber"),
            token_count=doc.get("tokenCount"),
            char_count=doc.get("charCount"),
            
            # Timestamps
            indexed_at=doc.get("indexedAt"),
            updated_at=doc.get("updatedAt"),
        )
    
    def _create_to_solr(self, chunk: ChunkCreate, chunk_id: str) -> Dict:
        """Convert ChunkCreate to Solr document."""
        now = datetime.utcnow().isoformat() + "Z"
        
        return {
            "id": chunk_id,
            "chunkId": chunk_id,
            "content": chunk.content,
            "documentId": chunk.document_id,
            "chunkIndex": chunk.chunk_index,
            
            # Denormalized fields
            "documentName": chunk.document_name,
            "title": chunk.title,
            "sourceUrl": chunk.source_url,
            "sourceDomain": chunk.source_domain,
            "category": chunk.category,
            "docType": chunk.doc_type,
            
            # Tax fields
            "taxYear": chunk.tax_year,
            "taxType": chunk.tax_type,
            "jurisdiction": chunk.jurisdiction,
            "state": chunk.state,
            "city": chunk.city,
            "authorityLevel": chunk.authority_level,
            
            # Governance
            "governanceState": chunk.governance_state.value if chunk.governance_state else None,
            "isLatestForTaxYear": chunk.is_latest_for_tax_year,
            
            # Vector
            "vector": chunk.vector,
            
            # Metadata
            "paragraphNumber": chunk.paragraph_number,
            "sectionTitle": chunk.section_title,
            "pageNumber": chunk.page_number,
            "tokenCount": len(chunk.content.split()) if chunk.content else 0,
            "charCount": len(chunk.content) if chunk.content else 0,
            
            # Timestamps
            "indexedAt": now,
            "updatedAt": now,
        }
    
    def get_chunk(self, chunk_id: str) -> Optional[ChunkResponse]:
        """Get a chunk by ID."""
        doc = self.solr.get_chunk(chunk_id)
        if not doc:
            return None
        return self._solr_to_response(doc)
    
    def list_chunks(
        self,
        query: str = "*:*",
        document_id: Optional[str] = None,
        filters: Optional[FilterParams] = None,
        page: int = 1,
        limit: int = 20,
        sort: str = "chunkIndex asc"
    ) -> Tuple[List[ChunkResponse], int]:
        """List chunks with filters and pagination."""
        fq = self._build_filters(filters)
        
        if document_id:
            fq.append(f"documentId:{document_id}")
        
        start = (page - 1) * limit
        
        docs, total = self.solr.search_chunks(
            query=query,
            filters=fq,
            start=start,
            rows=limit,
            sort=sort
        )
        
        return [self._solr_to_response(doc) for doc in docs], total
    
    def create_chunk(self, chunk: ChunkCreate, generate_embedding: bool = True) -> ChunkResponse:
        """Create a new chunk."""
        chunk_id = f"{chunk.document_id}_{chunk.chunk_index}"
        
        # Generate embedding if not provided and requested
        if generate_embedding and not chunk.vector and chunk.content:
            try:
                chunk.vector = self.embeddings.generate_embedding(chunk.content)
            except Exception:
                pass  # Continue without embedding
        
        solr_doc = self._create_to_solr(chunk, chunk_id)
        
        self.solr.create_chunk(solr_doc)
        
        return self.get_chunk(chunk_id)
    
    def create_chunks_bulk(self, request: BulkChunkCreate) -> BulkChunkResponse:
        """Create multiple chunks in bulk."""
        created = 0
        failed = 0
        errors = []
        
        solr_docs = []
        
        for chunk in request.chunks:
            try:
                chunk_id = f"{chunk.document_id}_{chunk.chunk_index}"
                
                # Generate embedding if requested
                if request.generate_embeddings and not chunk.vector and chunk.content:
                    try:
                        chunk.vector = self.embeddings.generate_embedding(chunk.content)
                    except Exception:
                        pass
                
                solr_doc = self._create_to_solr(chunk, chunk_id)
                solr_docs.append(solr_doc)
                
            except Exception as e:
                failed += 1
                errors.append(f"Chunk {chunk.chunk_index}: {str(e)}")
        
        # Bulk insert to Solr
        if solr_docs:
            try:
                self.solr.create_chunks_bulk(solr_docs)
                created = len(solr_docs)
            except Exception as e:
                failed += len(solr_docs)
                errors.append(f"Bulk insert failed: {str(e)}")
                created = 0
        
        return BulkChunkResponse(
            created=created,
            failed=failed,
            errors=errors
        )
    
    def update_chunk(self, chunk_id: str, updates: ChunkUpdate) -> Optional[ChunkResponse]:
        """Update a chunk."""
        existing = self.solr.get_chunk(chunk_id)
        if not existing:
            return None
        
        # Build update dict
        update_dict = {}
        update_data = updates.model_dump(exclude_unset=True)
        
        # Map field names
        field_mapping = {
            "content": "content",
            "vector": "vector",
            "paragraph_number": "paragraphNumber",
            "section_title": "sectionTitle",
            "page_number": "pageNumber",
            "document_name": "documentName",
            "title": "title",
            "source_url": "sourceUrl",
            "source_domain": "sourceDomain",
            "category": "category",
            "doc_type": "docType",
            "tax_year": "taxYear",
            "tax_type": "taxType",
            "jurisdiction": "jurisdiction",
            "state": "state",
            "city": "city",
            "authority_level": "authorityLevel",
            "governance_state": "governanceState",
            "is_latest_for_tax_year": "isLatestForTaxYear",
        }
        
        for py_field, solr_field in field_mapping.items():
            if py_field in update_data and update_data[py_field] is not None:
                value = update_data[py_field]
                if hasattr(value, "value"):  # Enum
                    value = value.value
                update_dict[solr_field] = value
        
        # Update token/char counts if content changed
        if "content" in update_dict:
            update_dict["tokenCount"] = len(update_dict["content"].split())
            update_dict["charCount"] = len(update_dict["content"])
        
        # Update timestamp
        update_dict["updatedAt"] = datetime.utcnow().isoformat() + "Z"
        
        self.solr.update_chunk(chunk_id, update_dict)
        
        return self.get_chunk(chunk_id)
    
    def delete_chunk(self, chunk_id: str) -> bool:
        """Delete a chunk."""
        return self.solr.delete_chunk(chunk_id)
    
    def delete_chunks_by_document(self, document_id: str) -> bool:
        """Delete all chunks for a document."""
        return self.solr.delete_chunks_by_document(document_id)
    
    def update_denormalized_fields(
        self,
        document_id: str,
        updates: Dict[str, Any]
    ) -> int:
        """Update denormalized fields on all chunks for a document."""
        # Get all chunks for document
        chunks, total = self.solr.get_chunks_by_document(document_id, rows=10000)
        
        updated = 0
        for chunk in chunks:
            try:
                self.solr.update_chunk(chunk["id"], updates)
                updated += 1
            except Exception:
                pass
        
        return updated


# Singleton instance
_chunk_service: Optional[ChunkService] = None


def get_chunk_service() -> ChunkService:
    """Get or create chunk service singleton."""
    global _chunk_service
    if _chunk_service is None:
        _chunk_service = ChunkService()
    return _chunk_service







"""Search service for hybrid RAG search."""

import time
from typing import List, Dict, Any, Optional, Tuple
from ..config import settings
from ..models.search import (
    SearchRequest,
    SearchQualityControls,
    RetrievedChunk,
    SourceDocument,
    SearchResponse,
)
from ..models.common import FilterParams
from .solr_service import get_solr_service, SolrService
from .embedding_service import get_embedding_service, EmbeddingService


class SearchService:
    """Service for hybrid search operations."""
    
    def __init__(
        self,
        solr_service: SolrService = None,
        embedding_service: EmbeddingService = None,
        alpha: float = None,
        beta: float = None,
        gamma: float = None
    ):
        self.solr = solr_service or get_solr_service()
        self.embeddings = embedding_service or get_embedding_service()
        
        # Hybrid scoring weights: final_score = BM25 * alpha + vector * beta + authority * gamma
        self.alpha = alpha or settings.bm25_weight
        self.beta = beta or settings.vector_weight
        self.gamma = gamma or settings.authority_weight
    
    def _build_filters(self, filters: Optional[FilterParams]) -> List[str]:
        """Build Solr filter queries from FilterParams."""
        fq = []
        
        if not filters:
            return fq
        
        if filters.jurisdiction:
            fq.append(f"jurisdiction:{filters.jurisdiction}")
        
        if filters.state:
            fq.append(f"state:{filters.state}")
        
        if filters.city:
            fq.append(f"city:{filters.city}")
        
        if filters.tax_year:
            fq.append(f"taxYear:{filters.tax_year}")
        
        if filters.category:
            categories = " OR ".join(filters.category)
            fq.append(f"category:({categories})")
        
        if filters.authority_level:
            fq.append(f"authorityLevel:{filters.authority_level}")
        
        if filters.governance_state:
            fq.append(f"governanceState:\"{filters.governance_state.value}\"")
        
        if filters.doc_type:
            fq.append(f"docType:{filters.doc_type}")
        
        if filters.source_domain:
            fq.append(f"sourceDomain:{filters.source_domain}")
        
        if filters.needs_human_review is not None:
            fq.append(f"needsHumanReview:{str(filters.needs_human_review).lower()}")
        
        if filters.is_latest_for_tax_year is not None:
            fq.append(f"isLatestForTaxYear:{str(filters.is_latest_for_tax_year).lower()}")
        
        # Only include published documents by default
        if not filters.governance_state:
            fq.append('governanceState:"Published"')
        
        return fq
    
    def _normalize_scores(self, scores: List[float]) -> List[float]:
        """Normalize scores to 0-1 range."""
        if not scores:
            return []
        
        min_score = min(scores)
        max_score = max(scores)
        
        if max_score == min_score:
            return [1.0] * len(scores)
        
        return [(s - min_score) / (max_score - min_score) for s in scores]
    
    def _calculate_authority_score(self, authority_level: Optional[int]) -> float:
        """Calculate authority score from level (1=highest, 6=lowest)."""
        if not authority_level:
            return 0.5  # Default mid-level score
        
        # Invert: level 1 -> 1.0, level 6 -> ~0.17
        return 1.0 / authority_level
    
    def _merge_results(
        self,
        bm25_results: List[Dict],
        vector_results: List[Dict],
        alpha: float,
        beta: float,
        gamma: float
    ) -> List[Dict]:
        """Merge and score results from BM25 and vector search."""
        # Create score maps
        bm25_scores = {doc["id"]: doc.get("score", 0) for doc in bm25_results}
        vector_scores = {doc["id"]: doc.get("score", 0) for doc in vector_results}
        
        # Normalize scores
        bm25_normalized = dict(zip(
            bm25_scores.keys(),
            self._normalize_scores(list(bm25_scores.values()))
        ))
        vector_normalized = dict(zip(
            vector_scores.keys(),
            self._normalize_scores(list(vector_scores.values()))
        ))
        
        # Combine all unique documents
        all_docs = {}
        for doc in bm25_results + vector_results:
            if doc["id"] not in all_docs:
                all_docs[doc["id"]] = doc
        
        # Calculate hybrid scores
        scored_docs = []
        for doc_id, doc in all_docs.items():
            bm25_score = bm25_normalized.get(doc_id, 0)
            vector_score = vector_normalized.get(doc_id, 0)
            authority_score = self._calculate_authority_score(doc.get("authorityLevel"))
            
            # Hybrid formula
            final_score = (
                alpha * bm25_score +
                beta * vector_score +
                gamma * authority_score
            )
            
            doc["relevanceScore"] = final_score
            doc["bm25Score"] = bm25_score
            doc["vectorScore"] = vector_score
            doc["authorityScore"] = authority_score
            scored_docs.append(doc)
        
        # Sort by final score
        scored_docs.sort(key=lambda x: x["relevanceScore"], reverse=True)
        
        return scored_docs
    
    def _doc_to_retrieved_chunk(self, doc: Dict, rank: int) -> RetrievedChunk:
        """Convert Solr document to RetrievedChunk model."""
        return RetrievedChunk(
            id=doc.get("id", ""),
            chunk_id=doc.get("chunkId", doc.get("id", "")),
            document_name=doc.get("documentName", ""),
            content=doc.get("content", ""),
            relevance_score=doc.get("relevanceScore", 0.0),
            authority_level=doc.get("authorityLevel"),
            priority_rank=rank,
            is_preferred=rank == 1,
            tax_year=doc.get("taxYear"),
            jurisdiction=doc.get("jurisdiction"),
            state=doc.get("state"),
            source_url=doc.get("sourceUrl"),
            source_domain=doc.get("sourceDomain"),
            paragraph_number=doc.get("paragraphNumber"),
            file_version=doc.get("fileVersion"),
            effective_from=doc.get("effectiveFrom"),
            conflict_resolution_reason=None
        )
    
    def _group_chunks_by_document(self, chunks: List[RetrievedChunk]) -> List[SourceDocument]:
        """Group chunks by their source document."""
        doc_map: Dict[str, SourceDocument] = {}
        
        for chunk in chunks:
            doc_id = chunk.id.rsplit("_", 1)[0] if "_" in chunk.id else chunk.id
            
            if doc_id not in doc_map:
                doc_map[doc_id] = SourceDocument(
                    id=doc_id,
                    title=chunk.document_name,
                    category=None,
                    jurisdiction=chunk.jurisdiction,
                    url=chunk.source_url,
                    excerpt=chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                    authority_level=chunk.authority_level,
                    priority_rank=chunk.priority_rank,
                    is_preferred=chunk.is_preferred,
                    tax_year=chunk.tax_year,
                    state=chunk.state,
                    effective_from=chunk.effective_from,
                    chunks=[]
                )
            
            doc_map[doc_id].chunks.append(chunk)
        
        # Sort by best chunk rank
        documents = list(doc_map.values())
        documents.sort(key=lambda d: min(c.priority_rank or 999 for c in d.chunks))
        
        return documents
    
    def search(self, request: SearchRequest) -> SearchResponse:
        """Perform hybrid RAG search."""
        start_time = time.time()
        
        # Get quality controls or defaults
        controls = request.search_quality_controls or SearchQualityControls()
        
        # Adjust weights based on controls
        alpha = self.alpha * (1 - controls.semantic_lexical_balance)
        beta = self.beta * controls.semantic_lexical_balance
        gamma = self.gamma * controls.authority_weight_control
        
        # Normalize weights
        total = alpha + beta + gamma
        if total > 0:
            alpha /= total
            beta /= total
            gamma /= total
        
        # Build filters
        filters = self._build_filters(request.filters)
        
        # Perform searches based on mode
        bm25_results = []
        vector_results = []
        
        if controls.retrieval_mode in ["hybrid", "bm25"]:
            bm25_results = self.solr.bm25_search(
                query=request.query,
                top_k=controls.top_k * 2,  # Get more for merging
                filters=filters
            )
        
        if controls.retrieval_mode in ["hybrid", "vector"]:
            try:
                query_vector = self.embeddings.generate_embedding(request.query)
                vector_results = self.solr.vector_search(
                    vector=query_vector,
                    top_k=controls.top_k * 2,
                    filters=filters
                )
            except Exception as e:
                # Fall back to BM25 only if embedding fails
                if controls.retrieval_mode == "vector":
                    raise
                # For hybrid, continue with BM25 only
                pass
        
        # Merge and score results
        if controls.retrieval_mode == "hybrid":
            merged_results = self._merge_results(
                bm25_results, vector_results, alpha, beta, gamma
            )
        elif controls.retrieval_mode == "vector":
            merged_results = vector_results
            for doc in merged_results:
                doc["relevanceScore"] = doc.get("score", 0)
        else:  # bm25
            merged_results = bm25_results
            for doc in merged_results:
                doc["relevanceScore"] = doc.get("score", 0)
        
        # Limit to top_k
        merged_results = merged_results[:controls.top_k]
        
        # Convert to response models
        retrieved_chunks = [
            self._doc_to_retrieved_chunk(doc, rank + 1)
            for rank, doc in enumerate(merged_results)
        ]
        
        source_documents = self._group_chunks_by_document(retrieved_chunks)
        
        search_time = (time.time() - start_time) * 1000
        
        return SearchResponse(
            query=request.query,
            retrieved_chunks=retrieved_chunks,
            source_documents=source_documents,
            total_chunks=len(retrieved_chunks),
            search_time_ms=search_time,
            retrieval_mode=controls.retrieval_mode,
            score_weights={
                "alpha": alpha,
                "beta": beta,
                "gamma": gamma
            }
        )
    
    def search_chunks(
        self,
        query: Optional[str] = None,
        document_id: Optional[str] = None,
        filters: Optional[FilterParams] = None,
        page: int = 1,
        limit: int = 20
    ) -> Tuple[List[RetrievedChunk], int]:
        """Search chunks with pagination."""
        fq = self._build_filters(filters)
        
        if document_id:
            fq.append(f"documentId:{document_id}")
        
        solr_query = query if query else "*:*"
        start = (page - 1) * limit
        
        docs, total = self.solr.search_chunks(
            query=solr_query,
            filters=fq,
            start=start,
            rows=limit
        )
        
        chunks = [
            self._doc_to_retrieved_chunk(doc, start + idx + 1)
            for idx, doc in enumerate(docs)
        ]
        
        return chunks, total


# Singleton instance
_search_service: Optional[SearchService] = None


def get_search_service() -> SearchService:
    """Get or create search service singleton."""
    global _search_service
    if _search_service is None:
        _search_service = SearchService()
    return _search_service


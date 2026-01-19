"""Async document service for document operations."""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from ..config import settings
from ..models.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    GovernanceStateUpdate,
    IngestionHistoryEvent,
    GovernanceHistoryEvent,
)
from ..models.common import FilterParams
from .solr_service import get_solr_service, SolrService
from .text_chunker import get_text_chunker
from .chunk_service import get_chunk_service


class DocumentService:
    """Async service for document CRUD operations."""

    def __init__(self, solr_service: SolrService = None):
        self.solr = solr_service or get_solr_service()

    def _format_date_for_solr(self, dt: Optional[datetime]) -> Optional[str]:
        """Format datetime for Solr (ISO 8601 with Z suffix)."""
        if dt is None:
            return None
        # Convert to UTC if timezone-aware, otherwise assume UTC
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc)
        else:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

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
            fq.append(f'governanceState:"{filters.governance_state.value}"')

        if filters.doc_type:
            fq.append(f"docType:{filters.doc_type}")

        if filters.source_domain:
            fq.append(f"sourceDomain:{filters.source_domain}")

        if filters.needs_human_review is not None:
            fq.append(f"needsHumanReview:{str(filters.needs_human_review).lower()}")

        if filters.is_latest_for_tax_year is not None:
            fq.append(
                f"isLatestForTaxYear:{str(filters.is_latest_for_tax_year).lower()}"
            )

        return fq

    def _solr_to_response(self, doc: Dict) -> DocumentResponse:
        """Convert Solr document to DocumentResponse model."""
        # Parse JSON history fields
        ingestion_history = []
        if doc.get("ingestionHistory"):
            try:
                history_data = json.loads(doc["ingestionHistory"])
                ingestion_history = [
                    IngestionHistoryEvent(**event) for event in history_data
                ]
            except (json.JSONDecodeError, TypeError):
                pass

        governance_history = []
        if doc.get("governanceHistory"):
            try:
                history_data = json.loads(doc["governanceHistory"])
                governance_history = [
                    GovernanceHistoryEvent(**event) for event in history_data
                ]
            except (json.JSONDecodeError, TypeError):
                pass

        return DocumentResponse(
            id=doc.get("id", ""),
            name=doc.get("name", doc.get("documentName", "")),
            title=doc.get("title"),
            description=doc.get("description"),
            source_url=doc.get("sourceUrl"),
            source_domain=doc.get("sourceDomain"),
            tags=doc.get("tags", []),
            category=doc.get("category"),
            doc_type=doc.get("docType"),
            form_family=doc.get("formFamily"),
            size=doc.get("size"),
            knowledge_base_id=doc.get("knowledgeBaseId", "default"),
            # Tax fields
            tax_year=doc.get("taxYear"),
            tax_type=doc.get("taxType"),
            jurisdiction=doc.get("jurisdiction"),
            state=doc.get("state"),
            city=doc.get("city"),
            authority_level=doc.get("authorityLevel"),
            authority_level_rationale=doc.get("authorityLevelRationale"),
            # Temporal
            effective_from=doc.get("effectiveFrom"),
            effective_to=doc.get("effectiveTo"),
            applies_to_tax_years=doc.get("appliesToTaxYears", []),
            applies_to_jurisdictions=doc.get("appliesToJurisdictions", []),
            # Status
            sync_status=doc.get("syncStatus", "synced"),
            index_status=doc.get("indexStatus", "not_indexed"),
            sync_error=doc.get("syncError"),
            index_error=doc.get("indexError"),
            # Governance
            governance_state=doc.get("governanceState", "Draft"),
            # RAG
            chunk_count=doc.get("chunkCount", 0),
            tokens_indexed=doc.get("tokensIndexed", 0),
            embedding_model=doc.get("embeddingModel"),
            last_indexed_at=doc.get("lastIndexedAt"),
            # Review
            needs_human_review=doc.get("needsHumanReview", False),
            review_reason=doc.get("reviewReason"),
            reviewed_at=doc.get("reviewedAt"),
            reviewed_by=doc.get("reviewedBy"),
            # Quality
            parsing_quality=doc.get("parsingQuality"),
            classification_confidence=doc.get("classificationConfidence"),
            # Version
            version=doc.get("version", 1),
            superseded_by=doc.get("supersededBy"),
            is_latest_for_tax_year=doc.get("isLatestForTaxYear", True),
            has_newer_version=doc.get("hasNewerVersion", False),
            # Timestamps
            uploaded_date=doc.get("uploadedDate"),
            last_synced=doc.get("lastSynced"),
            created_at=doc.get("createdAt"),
            updated_at=doc.get("updatedAt"),
            # History
            ingestion_history=ingestion_history,
            error_history=[],
            governance_history=governance_history,
        )

    def _create_to_solr(self, doc: DocumentCreate, doc_id: str) -> Dict:
        """Convert DocumentCreate to Solr document."""
        now = datetime.utcnow().isoformat() + "Z"

        # Initial ingestion history
        ingestion_history = [
            {"timestamp": now, "event": "created", "details": "Document created"}
        ]

        return {
            "id": doc_id,
            "name": doc.name,
            "documentName": doc.name,
            "title": doc.title,
            "description": doc.description,
            "sourceUrl": doc.source_url,
            "sourceDomain": doc.source_domain,
            "tags": doc.tags,
            "category": doc.category,
            "docType": doc.doc_type,
            "formFamily": doc.form_family,
            "size": doc.size,
            "knowledgeBaseId": doc.knowledge_base_id,
            # Tax fields
            "taxYear": doc.tax_year,
            "taxType": doc.tax_type,
            "jurisdiction": doc.jurisdiction,
            "state": doc.state,
            "city": doc.city,
            "authorityLevel": doc.authority_level,
            "authorityLevelRationale": doc.authority_level_rationale,
            # Temporal
            "effectiveFrom": self._format_date_for_solr(doc.effective_from),
            "effectiveTo": self._format_date_for_solr(doc.effective_to),
            "appliesToTaxYears": doc.applies_to_tax_years,
            "appliesToJurisdictions": doc.applies_to_jurisdictions,
            # Status defaults
            "syncStatus": "synced",
            "indexStatus": "not_indexed",
            "governanceState": "Draft",
            # RAG defaults
            "chunkCount": 0,
            "tokensIndexed": 0,
            # Review defaults
            "needsHumanReview": False,
            # Version
            "version": 1,
            "isLatestForTaxYear": True,
            "hasNewerVersion": False,
            # Timestamps
            "uploadedDate": now,
            "createdAt": now,
            "updatedAt": now,
            # History as JSON
            "ingestionHistory": json.dumps(ingestion_history),
            "governanceHistory": json.dumps([]),
            "errorHistory": json.dumps([]),
        }

    async def get_document(self, doc_id: str) -> Optional[DocumentResponse]:
        """Get a document by ID."""
        doc = await self.solr.get_document(doc_id)
        if not doc:
            return None
        return self._solr_to_response(doc)

    async def list_documents(
        self,
        query: str = "*:*",
        filters: Optional[FilterParams] = None,
        page: int = 1,
        limit: int = 20,
        sort: str = "uploadedDate desc",
    ) -> Tuple[List[DocumentResponse], int]:
        """List documents with filters and pagination."""
        fq = self._build_filters(filters)
        start = (page - 1) * limit

        docs, total = await self.solr.search_documents(
            query=query, filters=fq, start=start, rows=limit, sort=sort
        )

        return [self._solr_to_response(doc) for doc in docs], total

    async def create_document(self, doc: DocumentCreate) -> DocumentResponse:
        """Create a new document."""
        doc_id = str(uuid.uuid4())
        solr_doc = self._create_to_solr(doc, doc_id)

        await self.solr.create_document(solr_doc)

        return await self.get_document(doc_id)

    async def update_document(
        self, doc_id: str, updates: DocumentUpdate
    ) -> Optional[DocumentResponse]:
        """Update a document."""
        existing = await self.solr.get_document(doc_id)
        if not existing:
            return None

        # Build update dict (only non-None fields)
        update_dict = {}
        update_data = updates.model_dump(exclude_unset=True)

        # Map field names to Solr field names
        field_mapping = {
            "name": "name",
            "title": "title",
            "description": "description",
            "tags": "tags",
            "category": "category",
            "doc_type": "docType",
            "form_family": "formFamily",
            "tax_year": "taxYear",
            "tax_type": "taxType",
            "jurisdiction": "jurisdiction",
            "state": "state",
            "city": "city",
            "authority_level": "authorityLevel",
            "authority_level_rationale": "authorityLevelRationale",
            "effective_from": "effectiveFrom",
            "effective_to": "effectiveTo",
            "applies_to_tax_years": "appliesToTaxYears",
            "applies_to_jurisdictions": "appliesToJurisdictions",
            "superseded_by": "supersededBy",
        }

        for py_field, solr_field in field_mapping.items():
            if py_field in update_data and update_data[py_field] is not None:
                value = update_data[py_field]
                if isinstance(value, datetime):
                    value = self._format_date_for_solr(value)
                update_dict[solr_field] = value

        # Update timestamp
        update_dict["updatedAt"] = datetime.utcnow().isoformat() + "Z"

        await self.solr.update_document(doc_id, update_dict)

        return await self.get_document(doc_id)

    async def update_governance_state(
        self, doc_id: str, update: GovernanceStateUpdate
    ) -> Optional[DocumentResponse]:
        """Update document governance state."""
        existing = await self.solr.get_document(doc_id)
        if not existing:
            return None

        now = datetime.utcnow().isoformat() + "Z"

        # Get current governance history
        current_history = []
        if existing.get("governanceHistory"):
            try:
                current_history = json.loads(existing["governanceHistory"])
            except (json.JSONDecodeError, TypeError):
                pass

        # Add new history entry
        current_history.append(
            {
                "timestamp": now,
                "from_state": existing.get("governanceState"),
                "to_state": update.governance_state.value,
                "changed_by": update.changed_by,
                "reason": update.reason,
            }
        )

        # Update document
        update_dict = {
            "governanceState": update.governance_state.value,
            "governanceHistory": json.dumps(current_history),
            "updatedAt": now,
        }

        await self.solr.update_document(doc_id, update_dict)

        return await self.get_document(doc_id)

    async def delete_document(self, doc_id: str) -> bool:
        """Delete a document and its chunks."""
        # First delete all chunks
        await self.solr.delete_chunks_by_document(doc_id)

        # Then delete the document
        return await self.solr.delete_document(doc_id)

    async def get_document_chunks(
        self, doc_id: str, page: int = 1, limit: int = 100
    ) -> Tuple[List[Dict], int]:
        """Get all chunks for a document."""
        start = (page - 1) * limit
        return await self.solr.get_chunks_by_document(doc_id, start=start, rows=limit)

    async def process_and_chunk_document(
        self,
        doc_id: str,
        text: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        generate_embeddings: bool = True,
    ) -> Tuple[int, List[str]]:
        """
        Process a document's text content and create chunks.

        This method:
        1. Splits the document text into chunks using LangChain text splitter
        2. Creates chunks in Solr with embeddings
        3. Updates document metadata (chunk_count, index_status)

        Args:
            doc_id: Document ID to process
            text: Full document text content
            chunk_size: Optional custom chunk size in tokens
            chunk_overlap: Optional custom chunk overlap in tokens
            generate_embeddings: Whether to generate embeddings for chunks

        Returns:
            Tuple of (chunks_created, error_messages)
        """
        # Get document
        document = await self.get_document(doc_id)
        if not document:
            return 0, [f"Document {doc_id} not found"]

        # Delete existing chunks if any
        await self.solr.delete_chunks_by_document(doc_id)

        # Get text chunker and chunk service
        # Note: text_chunker is sync (CPU-bound) - run in thread pool
        chunker = get_text_chunker()
        chunk_service = get_chunk_service()

        errors = []
        chunks_created = 0

        try:
            # Split text into chunks - run in thread pool since it's CPU-bound
            chunks = await asyncio.to_thread(
                chunker.chunk_document,
                document=document,
                text=text,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

            if not chunks:
                errors.append("No chunks created from document text")
                # Update document status
                await self.solr.update_document(
                    doc_id,
                    {
                        "indexStatus": "index_failed",
                        "indexError": "No chunks created from document text",
                        "chunkCount": 0,
                    },
                )
                return 0, errors

            # Create chunks in bulk with embeddings
            from ..models.chunk import BulkChunkCreate

            bulk_request = BulkChunkCreate(
                chunks=chunks, generate_embeddings=generate_embeddings
            )

            result = await chunk_service.create_chunks_bulk(bulk_request)
            chunks_created = result.created

            if result.failed > 0:
                errors.extend(result.errors)

            # Calculate total tokens
            total_tokens = sum(len(chunk.content.split()) for chunk in chunks)

            # Update document with chunk metadata
            now = datetime.utcnow().isoformat() + "Z"
            update_dict = {
                "chunkCount": chunks_created,
                "tokensIndexed": total_tokens,
                "indexStatus": "indexed" if chunks_created > 0 else "index_failed",
                "lastIndexedAt": now,
                "embeddingModel": settings.embedding_model
                if generate_embeddings
                else None,
            }

            if errors:
                update_dict["indexError"] = "; ".join(
                    errors[:3]
                )  # Limit error message length

            await self.solr.update_document(doc_id, update_dict)

            # Update ingestion history
            existing = await self.solr.get_document(doc_id)
            if existing:
                ingestion_history = []
                if existing.get("ingestionHistory"):
                    try:
                        ingestion_history = json.loads(existing["ingestionHistory"])
                    except (json.JSONDecodeError, TypeError):
                        pass

                ingestion_history.append(
                    {
                        "timestamp": now,
                        "event": "indexed",
                        "details": f"{chunks_created} chunks created, {total_tokens} tokens indexed",
                    }
                )

                await self.solr.update_document(
                    doc_id, {"ingestionHistory": json.dumps(ingestion_history)}
                )

        except Exception as e:
            error_msg = f"Error processing document: {str(e)}"
            errors.append(error_msg)

            # Update document with error status
            await self.solr.update_document(
                doc_id,
                {
                    "indexStatus": "index_failed",
                    "indexError": error_msg,
                    "chunkCount": 0,
                },
            )

        return chunks_created, errors


# Singleton instance
_document_service: Optional[DocumentService] = None


def get_document_service() -> DocumentService:
    """Get or create document service singleton."""
    global _document_service
    if _document_service is None:
        _document_service = DocumentService()
    return _document_service

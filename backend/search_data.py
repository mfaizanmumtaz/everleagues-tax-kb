from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
import requests
import json
import sys
from typing import Optional, Dict, List, Tuple

load_dotenv()


# final_score = BM25_score × α + vector_score × β + authority_weight × γ

# Configuration
SOLR_URL = "http://localhost:8983/solr/tax_docs_v2"
SOLR_SELECT_URL = f"{SOLR_URL}/select"
EMBEDDING_MODEL = "text-embedding-3-small"

# Hybrid scoring weights
DEFAULT_ALPHA = 0.3  # BM25 weight
DEFAULT_BETA = 0.5   # Vector similarity weight
DEFAULT_GAMMA = 0.4  # Authority weight

class HybridTaxSearch:
    """
    Implements hybrid search with the formula:
    final_score = BM25_score × α + vector_score × β + authority_weight × γ
    """
    
    def __init__(
        self,
        solr_url: str = SOLR_URL,
        embedding_model: str = EMBEDDING_MODEL,
        alpha: float = DEFAULT_ALPHA,
        beta: float = DEFAULT_BETA,
        gamma: float = DEFAULT_GAMMA
    ):
        self.solr_url = solr_url
        self.select_url = f"{solr_url}/select"
        self.embedding_model_name = embedding_model
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        
        # Initialize embedding model
        print(f"📦 Loading embedding model: {embedding_model}...")
        try:
            self.model = OpenAIEmbeddings(model=embedding_model)
            print(f"✅ Model loaded successfully!")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            raise
    
    def check_connection(self) -> bool:
        """Check if Solr is accessible"""
        try:
            response = requests.get(f"{self.solr_url}/admin/ping", timeout=5)
            if response.status_code == 200:
                print(f"✅ Connected to Solr: {self.solr_url}")
                return True
            else:
                print(f"❌ Solr ping failed: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print(f"❌ Cannot connect to Solr at {self.solr_url}")
            return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def _vector_search(
        self,
        query_embedding: List[float],
        top_k: int,
        filters: Optional[List[str]] = None
    ) -> Dict:
        """Perform vector similarity search"""
        
        vector_str = '[' + ','.join(map(str, query_embedding)) + ']'
        
        params = {
            'q': f'{{!knn f=vector topK={top_k}}}{vector_str}',
            'fl': 'id,title,content,excerpt,score,sourceUrl,category,jurisdiction,state,taxYear,authorityLevel,docType,documentName,governanceState,isLatestForTaxYear',
            'rows': top_k,
            'wt': 'json'
        }
        
        if filters:
            params['fq'] = filters
        
        try:
            response = requests.post(
                self.select_url,
                data=params,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️  Vector search error: HTTP {response.status_code}")
                return {'response': {'docs': [], 'numFound': 0}}
        except Exception as e:
            print(f"⚠️  Vector search error: {e}")
            return {'response': {'docs': [], 'numFound': 0}}
    
    def _bm25_search(
        self,
        query_text: str,
        top_k: int,
        filters: Optional[List[str]] = None
    ) -> Dict:
        """Perform BM25 keyword search"""
        
        params = {
            'q': query_text,
            'defType': 'edismax',
            'qf': 'content^2 title^3 excerpt^1.5',
            'fl': 'id,title,content,excerpt,score,sourceUrl,category,jurisdiction,state,taxYear,authorityLevel,docType,documentName,governanceState,isLatestForTaxYear',
            'rows': top_k,
            'wt': 'json'
        }
        
        if filters:
            params['fq'] = filters
        
        try:
            response = requests.post(
                self.select_url,
                data=params,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️  BM25 search error: HTTP {response.status_code}")
                return {'response': {'docs': [], 'numFound': 0}}
        except Exception as e:
            print(f"⚠️  BM25 search error: {e}")
            return {'response': {'docs': [], 'numFound': 0}}
    
    def _normalize_scores(self, docs: List[Dict], score_key: str = 'score') -> List[Dict]:
        """Normalize scores to 0-1 range"""
        if not docs:
            return docs
        
        max_score = max([doc.get(score_key, 0) for doc in docs])
        
        if max_score == 0:
            return docs
        
        for doc in docs:
            doc[f'{score_key}_normalized'] = doc.get(score_key, 0) / max_score
        
        return docs
    
    def _calculate_authority_weight(self, authority_level: int) -> float:
        """
        Calculate authority weight (0-1 scale)
        Lower authority level = higher weight
        Level 1 (statute) = 1.0
        Level 5 (commentary) = 0.2
        """
        if authority_level is None:
            return 0.5  # Default mid-level
        
        # Invert: level 1 = highest weight
        return (6 - min(authority_level, 5)) / 5
    
    def hybrid_search(
        self,
        query_text: str,
        top_k: int = 10,
        filters: Optional[Dict] = None,
        alpha: Optional[float] = None,
        beta: Optional[float] = None,
        gamma: Optional[float] = None
    ) -> List[Dict]:
        """
        Perform hybrid search with formula:
        final_score = BM25_score × α + vector_score × β + authority_weight × γ
        
        Args:
            query_text: Search query
            top_k: Number of results to return
            filters: Optional filters (jurisdiction, taxYear, category, state, etc.)
            alpha: BM25 weight (default: 0.3)
            beta: Vector weight (default: 0.5)
            gamma: Authority weight (default: 0.2)
        
        Returns:
            List of documents with hybrid scores
        """
        
        # Use instance defaults if not provided
        alpha = alpha if alpha is not None else self.alpha
        beta = beta if beta is not None else self.beta
        gamma = gamma if gamma is not None else self.gamma
        
        print(f"\n🔍 Query: '{query_text}'")
        print(f"📊 Weights: α(BM25)={alpha}, β(Vector)={beta}, γ(Authority)={gamma}")
        
        # Build filter queries
        filter_queries = []
        if filters:
            if filters.get('jurisdiction'):
                filter_queries.append(f'jurisdiction:"{filters["jurisdiction"]}"')
            if filters.get('tax_year'):
                filter_queries.append(f'taxYear:{filters["tax_year"]}')
            if filters.get('category'):
                filter_queries.append(f'category:"{filters["category"]}"')
            if filters.get('state'):
                filter_queries.append(f'state:"{filters["state"]}"')
            if filters.get('doc_type'):
                filter_queries.append(f'docType:"{filters["doc_type"]}"')
            if filters.get('governance_state'):
                filter_queries.append(f'governanceState:"{filters["governance_state"]}"')
            if filters.get('is_latest'):
                filter_queries.append(f'isLatestForTaxYear:{str(filters["is_latest"]).lower()}')
        
        if filter_queries:
            print(f"🔽 Filters: {', '.join(filter_queries)}")
        
        # Get more candidates than needed for better ranking
        candidate_k = top_k * 3
        
        # Step 1: Vector search
        print(f"\n🧠 Performing vector search (topK={candidate_k})...")
        query_embedding = self.model.embed_query(query_text)
        vector_results = self._vector_search(query_embedding, candidate_k, filter_queries)
        vector_docs = {doc['id']: doc for doc in vector_results['response']['docs']}
        print(f"   Found {len(vector_docs)} vector results")
        
        # Step 2: BM25 search
        print(f"📝 Performing BM25 search (topK={candidate_k})...")
        bm25_results = self._bm25_search(query_text, candidate_k, filter_queries)
        bm25_docs = {doc['id']: doc for doc in bm25_results['response']['docs']}
        print(f"   Found {len(bm25_docs)} BM25 results")
        
        # Step 3: Merge and calculate hybrid scores
        print(f"\n⚙️  Calculating hybrid scores...")
        
        # Normalize scores
        self._normalize_scores(list(vector_docs.values()), 'score')
        self._normalize_scores(list(bm25_docs.values()), 'score')
        
        # Combine all unique documents
        all_doc_ids = set(vector_docs.keys()) | set(bm25_docs.keys())
        hybrid_results = []
        
        for doc_id in all_doc_ids:
            # Get normalized scores (0 if document not in that result set)
            vector_score = vector_docs.get(doc_id, {}).get('score_normalized', 0)
            bm25_score = bm25_docs.get(doc_id, {}).get('score_normalized', 0)
            
            # Get document (prefer vector result if in both)
            doc = vector_docs.get(doc_id) or bm25_docs.get(doc_id)
            
            # Calculate authority weight
            authority_level = self._format_field_value(doc.get('authorityLevel', 3))
            authority_weight = self._calculate_authority_weight(authority_level)
            
            # Calculate hybrid score using the formula
            hybrid_score = (bm25_score * alpha) + (vector_score * beta) + (authority_weight * gamma)
            
            # Add score components to document
            doc['hybrid_score'] = hybrid_score
            doc['bm25_score'] = bm25_score
            doc['vector_score'] = vector_score
            doc['authority_weight'] = authority_weight
            doc['authority_level'] = authority_level
            
            hybrid_results.append(doc)
        
        # Sort by hybrid score
        hybrid_results.sort(key=lambda x: x['hybrid_score'], reverse=True)
        
        print(f"✅ Hybrid scoring complete. Returning top {top_k} results.\n")
        
        return hybrid_results[:top_k]
    
    def _format_field_value(self, field_value):
        """Format field value (handle lists)"""
        if isinstance(field_value, list):
            return field_value[0] if field_value else None
        return field_value
    
    def display_results(self, results: List[Dict], query_text: str):
        """Display search results with detailed scoring breakdown"""
        
        print("=" * 100)
        print(f"🎯 Hybrid Search Results for: '{query_text}'")
        print("=" * 100)
        print(f"📊 Found {len(results)} document(s)\n")
        
        if not results:
            print("❌ No results found!")
            print("\n💡 Suggestions:")
            print("   - Try different keywords")
            print("   - Remove or adjust filters")
            print("   - Check if documents are indexed in Solr")
            return
        
        for i, doc in enumerate(results, 1):
            # Extract fields
            title = self._format_field_value(doc.get('title', 'Untitled'))
            content = self._format_field_value(doc.get('content', ''))
            excerpt = self._format_field_value(doc.get('excerpt'))
            
            # Scores
            hybrid_score = doc.get('hybrid_score', 0)
            bm25_score = doc.get('bm25_score', 0)
            vector_score = doc.get('vector_score', 0)
            authority_weight = doc.get('authority_weight', 0)
            
            # Metadata
            category = self._format_field_value(doc.get('category'))
            jurisdiction = self._format_field_value(doc.get('jurisdiction'))
            state = self._format_field_value(doc.get('state'))
            tax_year = self._format_field_value(doc.get('taxYear'))
            authority_level = self._format_field_value(doc.get('authorityLevel'))
            doc_type = self._format_field_value(doc.get('docType'))
            document_name = self._format_field_value(doc.get('documentName'))
            source_url = self._format_field_value(doc.get('sourceUrl'))
            governance = self._format_field_value(doc.get('governanceState'))
            is_latest = self._format_field_value(doc.get('isLatestForTaxYear'))
            
            # Display result
            print(f"\n{'─' * 100}")
            print(f"📄 Result {i} │ Hybrid Score: {hybrid_score:.4f}")
            print(f"{'─' * 100}")
            print(f"Title: {title}")
            
            if document_name:
                print(f"Document: {document_name}")
            
            # Score breakdown
            print(f"\n📊 Score Breakdown:")
            print(f"   • BM25 (keyword):     {bm25_score:.3f} × {self.alpha} = {bm25_score * self.alpha:.4f}")
            print(f"   • Vector (semantic):  {vector_score:.3f} × {self.beta} = {vector_score * self.beta:.4f}")
            print(f"   • Authority:          {authority_weight:.3f} × {self.gamma} = {authority_weight * self.gamma:.4f}")
            print(f"   • Final Hybrid Score: {hybrid_score:.4f}")
            
            # Content preview
            if excerpt:
                print(f"\n📝 {excerpt}")
            elif content:
                preview = content[:250] + "..." if len(content) > 250 else content
                print(f"\n📝 {preview}")
            
            # Metadata
            metadata_parts = []
            if category:
                metadata_parts.append(f"📁 {category}")
            if jurisdiction:
                metadata_parts.append(f"⚖️ {jurisdiction}")
            if state:
                metadata_parts.append(f"📍 {state}")
            if tax_year:
                metadata_parts.append(f"📅 {tax_year}")
            if authority_level:
                metadata_parts.append(f"⭐ Authority Lvl {authority_level}")
            if doc_type:
                metadata_parts.append(f"📋 {doc_type}")
            if governance:
                metadata_parts.append(f"✓ {governance}")
            if is_latest:
                metadata_parts.append("🆕 Latest")
            
            if metadata_parts:
                print(f"\n{' │ '.join(metadata_parts)}")
            
            if source_url:
                print(f"\n🔗 {source_url}")


def main():
    """Main function with usage examples"""
    
    print("=" * 100)
    print("🚀 EverLeagues Tax Knowledge Base - Hybrid Search System")
    print("=" * 100)
    print("\nFormula: final_score = BM25_score × α + vector_score × β + authority_weight × γ")
    print(f"Default Weights: α={DEFAULT_ALPHA}, β={DEFAULT_BETA}, γ={DEFAULT_GAMMA}\n")
    
    # Initialize search engine
    try:
        search_engine = HybridTaxSearch(
            solr_url=SOLR_URL,
            embedding_model=EMBEDDING_MODEL,
            alpha=DEFAULT_ALPHA,
            beta=DEFAULT_BETA,
            gamma=DEFAULT_GAMMA
        )
    except Exception as e:
        print(f"❌ Failed to initialize search engine: {e}")
        sys.exit(1)
    
    # Check Solr connection
    if not search_engine.check_connection():
        print("\n❌ Exiting. Please ensure Solr is running.")
        sys.exit(1)
    
    # Example 1: Basic hybrid search
    print("\n" + "=" * 100)
    print("Example 1: Basic Hybrid Search")
    print("=" * 100)
    
    results = search_engine.hybrid_search(
        query_text="What is the standard deduction for married couples filing jointly?",
        top_k=5
    )
    
    search_engine.display_results(results, "standard deduction for married couples")
    
    # Example 2: Filtered search with custom weights
    print("\n\n" + "=" * 100)
    print("Example 2: Filtered Search (Federal, 2024) with Custom Weights")
    print("=" * 100)
    
    results = search_engine.hybrid_search(
        query_text="retirement contribution limits",
        top_k=5,
        filters={
            'jurisdiction': 'federal',
            'tax_year': 2024,
            'category': 'regulations',
            'governance_state': 'Published',
            'is_latest': True
        },
        alpha=0.2,  # Lower keyword weight
        beta=0.6,   # Higher semantic weight
        gamma=0.2   # Standard authority weight
    )
    
    search_engine.display_results(results, "retirement contribution limits (federal, 2024)")
    
    # Example 3: State-specific search
    print("\n\n" + "=" * 100)
    print("Example 3: State-Specific Search (New York)")
    print("=" * 100)
    
    results = search_engine.hybrid_search(
        query_text="state income tax rates and brackets",
        top_k=3,
        filters={
            'jurisdiction': 'state',
            'state': 'NY',
            'tax_year': 2024
        }
    )
    
    search_engine.display_results(results, "NY income tax rates")
    
    print("\n" + "=" * 100)
    print("✅ Hybrid search examples completed!")
    print("=" * 100)


if __name__ == "__main__":
    main()
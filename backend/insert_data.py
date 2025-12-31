from langchain_openai import OpenAIEmbeddings
import requests
from dotenv import load_dotenv
from datetime import datetime
import sys
import json

load_dotenv()

# Configuration
SOLR_URL = "http://localhost:8983/solr/tax_docs_v2"
SOLR_UPDATE_URL = f"{SOLR_URL}/update"
EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100  # Process documents in batches

def check_solr_connection():
    """Check if Solr is accessible"""
    try:
        response = requests.get(f"{SOLR_URL}/admin/ping")
        if response.status_code == 200:
            print("✅ Solr connection successful")
            return True
        else:
            print(f"❌ Solr ping failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Solr. Please ensure Solr is running on http://localhost:8983")
        return False
    except Exception as e:
        print(f"❌ Error connecting to Solr: {e}")
        return False

def format_date_for_solr(date_str):
    """Convert date string to Solr date format (ISO 8601)"""
    if not date_str:
        return None
    try:
        # Try parsing common date formats
        if isinstance(date_str, str):
            # If already in ISO format, return as is
            if 'T' in date_str or date_str.endswith('Z'):
                return date_str
            # Try parsing and converting
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        return date_str
    except Exception as e:
        print(f"⚠️  Warning: Could not parse date '{date_str}': {e}")
        return None

def prepare_document(doc, embedding):
    """Prepare a document for Solr insertion with all fields"""
    solr_doc = {
        'id': doc.get('id'),
        'title': doc.get('title'),
        'content': doc.get('content'),
        'vector': embedding
    }
    
    # Add optional fields if they exist
    optional_fields = [
        'chunkId', 'documentName', 'sourceUrl', 'sourceDomain',
        'category', 'jurisdiction', 'state', 'taxYear',
        'effectiveFrom', 'effectiveTo', 'appliesToTaxYears',
        'appliesToJurisdictions', 'authorityLevel', 'authorityLevelRationale',
        'docType', 'formFamily', 'version', 'fileVersion', 'revisionDate',
        'paragraphNumber', 'priorityRank', 'relevanceScore', 'isPreferred',
        'conflictResolutionReason', 'replacedBy', 'supersededBy',
        'supersededByVersionId', 'hasNewerVersion', 'isLatestForTaxYear',
        'lastCrawled', 'lastEmbedded', 'chunkCount', 'tokensIndexed',
        'embeddingModel', 'parsingQuality', 'classificationConfidence',
        'needsHumanReview', 'reviewReason', 'reviewedAt', 'reviewedBy',
        'governanceState', 'excerpt', 'url', 'supersessionChain'
    ]
    
    for field in optional_fields:
        value = doc.get(field)
        if value is not None:
            # Handle date fields
            if field in ['effectiveFrom', 'effectiveTo', 'revisionDate', 
                        'lastCrawled', 'lastEmbedded', 'reviewedAt']:
                formatted_date = format_date_for_solr(value)
                if formatted_date:
                    solr_doc[field] = formatted_date
            else:
                solr_doc[field] = value
    
    return solr_doc

def insert_documents(documents, commit=True):
    """Insert documents into Solr"""
    try:
        # Prepare the payload - Solr expects a list of documents
        payload = documents
        
        params = {}
        if commit:
            params['commit'] = 'true'
        
        response = requests.post(
            SOLR_UPDATE_URL,
            json=payload,
            params=params,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('responseHeader', {}).get('status') == 0:
                return True, f"Successfully inserted {len(documents)} documents"
            else:
                return False, f"Solr returned error: {result}"
        else:
            return False, f"HTTP {response.status_code}: {response.text}"
            
    except requests.exceptions.ConnectionError:
        return False, "Connection error while inserting documents"
    except Exception as e:
        return False, f"Error inserting documents: {e}"

def main():
    print("🚀 Starting tax documents insertion into Solr...\n")
    
    # Check Solr connection
    if not check_solr_connection():
        print("\n❌ Exiting. Please ensure Solr is running.")
        sys.exit(1)
    
    # Initialize embedding model
    print("\n📦 Loading embedding model...")
    try:
        model = OpenAIEmbeddings(model=EMBEDDING_MODEL)
        print(f"✅ Model '{EMBEDDING_MODEL}' loaded!")
    except Exception as e:
        print(f"❌ Error loading embedding model: {e}")
        print("   Please ensure OPENAI_API_KEY is set in your .env file")
        sys.exit(1)
    
    # Sample tax documents with comprehensive metadata
    documents = [
        {
            "id": "doc_001",
            "title": "Section 179 Deduction",
            "content": "Section 179 allows businesses to deduct the full purchase price of qualifying equipment and software purchased or financed during the tax year. This deduction can significantly reduce taxable income.",
            "chunkId": "chunk_001_001",
            "documentName": "IRS_Publication_946_2024.pdf",
            "sourceUrl": "https://www.irs.gov/pub/irs-pdf/p946.pdf",
            "sourceDomain": "irs.gov",
            "category": "regulations",
            "jurisdiction": "federal",
            "taxYear": 2024,
            "effectiveFrom": "2024-01-01T00:00:00Z",
            "appliesToTaxYears": [2024, 2025],
            "appliesToJurisdictions": ["federal"],
            "authorityLevel": 1,
            "authorityLevelRationale": "IRS Publication - highest authority",
            "docType": "publication",
            "version": "2024",
            "revisionDate": "2024-01-15T00:00:00Z",
            "embeddingModel": EMBEDDING_MODEL,
            "parsingQuality": "ok",
            "isLatestForTaxYear": True,
            "governanceState": "Published",
            "excerpt": "Section 179 allows businesses to deduct the full purchase price of qualifying equipment."
        },
        {
            "id": "doc_002",
            "title": "Standard Deduction 2024",
            "content": "The standard deduction for married couples filing jointly is $27,700 for tax year 2024. For single taxpayers and married individuals filing separately, it is $14,600. For heads of households, the standard deduction is $21,900.",
            "chunkId": "chunk_002_001",
            "documentName": "Form_1040_Instructions_2024.pdf",
            "sourceUrl": "https://www.irs.gov/pub/irs-pdf/i1040gi.pdf",
            "sourceDomain": "irs.gov",
            "category": "instructions",
            "jurisdiction": "federal",
            "taxYear": 2024,
            "effectiveFrom": "2024-01-01T00:00:00Z",
            "appliesToTaxYears": [2024],
            "appliesToJurisdictions": ["federal"],
            "authorityLevel": 1,
            "docType": "instructions",
            "formFamily": "1040",
            "version": "2024",
            "embeddingModel": EMBEDDING_MODEL,
            "parsingQuality": "ok",
            "isLatestForTaxYear": True,
            "governanceState": "Published",
            "excerpt": "Standard deduction amounts for tax year 2024 vary by filing status."
        },
        {
            "id": "doc_003",
            "title": "Capital Gains Tax",
            "content": "Long-term capital gains are taxed at 0%, 15%, or 20% depending on your taxable income and filing status. Short-term capital gains are taxed as ordinary income.",
            "chunkId": "chunk_003_001",
            "documentName": "IRS_Publication_544_2024.pdf",
            "sourceUrl": "https://www.irs.gov/pub/irs-pdf/p544.pdf",
            "sourceDomain": "irs.gov",
            "category": "regulations",
            "jurisdiction": "federal",
            "taxYear": 2024,
            "effectiveFrom": "2024-01-01T00:00:00Z",
            "appliesToTaxYears": [2024],
            "appliesToJurisdictions": ["federal"],
            "authorityLevel": 1,
            "docType": "publication",
            "version": "2024",
            "embeddingModel": EMBEDDING_MODEL,
            "parsingQuality": "ok",
            "isLatestForTaxYear": True,
            "governanceState": "Published",
            "excerpt": "Capital gains tax rates depend on holding period and income level."
        },
        {
            "id": "doc_004",
            "title": "Home Office Deduction",
            "content": "If you use part of your home exclusively and regularly for business, you may be able to deduct expenses like mortgage interest, insurance, utilities, repairs, and depreciation.",
            "chunkId": "chunk_004_001",
            "documentName": "IRS_Publication_587_2024.pdf",
            "sourceUrl": "https://www.irs.gov/pub/irs-pdf/p587.pdf",
            "sourceDomain": "irs.gov",
            "category": "regulations",
            "jurisdiction": "federal",
            "taxYear": 2024,
            "effectiveFrom": "2024-01-01T00:00:00Z",
            "appliesToTaxYears": [2024],
            "appliesToJurisdictions": ["federal"],
            "authorityLevel": 1,
            "docType": "publication",
            "version": "2024",
            "embeddingModel": EMBEDDING_MODEL,
            "parsingQuality": "ok",
            "isLatestForTaxYear": True,
            "governanceState": "Published",
            "excerpt": "Home office deduction requirements and eligible expenses."
        },
        {
            "id": "doc_005",
            "title": "Retirement Contributions",
            "content": "Contributions to traditional IRAs and 401(k) plans can reduce your taxable income. For 2024, the contribution limit for 401(k) plans is $23,000, with an additional $7,500 catch-up contribution for those 50 and older.",
            "chunkId": "chunk_005_001",
            "documentName": "IRS_Publication_590_2024.pdf",
            "sourceUrl": "https://www.irs.gov/pub/irs-pdf/p590a.pdf",
            "sourceDomain": "irs.gov",
            "category": "regulations",
            "jurisdiction": "federal",
            "taxYear": 2024,
            "effectiveFrom": "2024-01-01T00:00:00Z",
            "appliesToTaxYears": [2024],
            "appliesToJurisdictions": ["federal"],
            "authorityLevel": 1,
            "docType": "publication",
            "version": "2024",
            "embeddingModel": EMBEDDING_MODEL,
            "parsingQuality": "ok",
            "isLatestForTaxYear": True,
            "governanceState": "Published",
            "excerpt": "Retirement contribution limits and tax benefits for 2024."
        },
        {
            "id": "doc_006",
            "title": "New York State Income Tax Rates",
            "content": "New York State has a progressive income tax system with rates ranging from 4% to 10.9% depending on income level and filing status. The tax applies to New York source income for residents and non-residents.",
            "chunkId": "chunk_006_001",
            "documentName": "NY_Tax_Guide_2024.pdf",
            "sourceUrl": "https://www.tax.ny.gov/pit/file/",
            "sourceDomain": "tax.ny.gov",
            "category": "regulations",
            "jurisdiction": "state",
            "state": "NY",
            "taxYear": 2024,
            "effectiveFrom": "2024-01-01T00:00:00Z",
            "appliesToTaxYears": [2024],
            "appliesToJurisdictions": ["NY"],
            "authorityLevel": 2,
            "docType": "publication",
            "version": "2024",
            "embeddingModel": EMBEDDING_MODEL,
            "parsingQuality": "ok",
            "isLatestForTaxYear": True,
            "governanceState": "Published",
            "excerpt": "New York State income tax rates and filing requirements."
        },
        {
            "id": "doc_007",
            "title": "California Sales Tax Guide",
            "content": "California's statewide sales tax rate is 7.25%. Local jurisdictions can add additional taxes, making the total rate vary by location. Most goods and services are subject to sales tax, with some exemptions.",
            "chunkId": "chunk_007_001",
            "documentName": "CA_Sales_Tax_Guide_2024.pdf",
            "sourceUrl": "https://www.cdtfa.ca.gov/taxes-and-fees/",
            "sourceDomain": "cdtfa.ca.gov",
            "category": "sales-tax",
            "jurisdiction": "state",
            "state": "CA",
            "taxYear": 2024,
            "effectiveFrom": "2024-01-01T00:00:00Z",
            "appliesToTaxYears": [2024],
            "appliesToJurisdictions": ["CA"],
            "authorityLevel": 2,
            "docType": "publication",
            "version": "2024",
            "embeddingModel": EMBEDDING_MODEL,
            "parsingQuality": "ok",
            "isLatestForTaxYear": True,
            "governanceState": "Published",
            "excerpt": "California sales tax rates and exemptions."
        }
    ]
    
    # Process and prepare documents
    print(f"\n📝 Processing {len(documents)} documents...")
    solr_docs = []
    
    for i, doc in enumerate(documents, 1):
        try:
            # Generate embedding
            embedding = model.embed_query(doc['content'])
            
            # Prepare document for Solr
            solr_doc = prepare_document(doc, embedding)
            solr_docs.append(solr_doc)
            
            print(f"  ✓ [{i}/{len(documents)}] Processed: {doc['title']}")
            
        except Exception as e:
            print(f"  ❌ Error processing document '{doc.get('title', 'unknown')}': {e}")
            continue
    
    if not solr_docs:
        print("\n❌ No documents to insert. Exiting.")
        sys.exit(1)
    
    # Insert documents in batches
    print(f"\n💾 Inserting {len(solr_docs)} documents into Solr...")
    
    total_inserted = 0
    for i in range(0, len(solr_docs), BATCH_SIZE):
        batch = solr_docs[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (len(solr_docs) + BATCH_SIZE - 1) // BATCH_SIZE
        
        print(f"  Inserting batch {batch_num}/{total_batches} ({len(batch)} documents)...")
        
        # Commit only on the last batch
        commit = (i + BATCH_SIZE >= len(solr_docs))
        success, message = insert_documents(batch, commit=commit)
        
        if success:
            total_inserted += len(batch)
            print(f"  ✅ Batch {batch_num} inserted successfully")
        else:
            print(f"  ❌ Batch {batch_num} failed: {message}")
            # Continue with other batches even if one fails
    
    # Final commit if we didn't commit in batches
    if len(solr_docs) <= BATCH_SIZE:
        print("\n🔄 Committing changes...")
        commit_response = requests.post(
            f"{SOLR_UPDATE_URL}?commit=true",
            json=[],
            headers={'Content-Type': 'application/json'}
        )
        if commit_response.status_code == 200:
            print("✅ Commit successful")
    
    print("\n" + "="*60)
    print(f"🎉 Insertion complete! {total_inserted}/{len(solr_docs)} documents inserted.")
    print("="*60)
    
    # Verify insertion
    print("\n🔍 Verifying insertion...")
    try:
        verify_response = requests.get(
            f"{SOLR_URL}/select",
            params={'q': '*:*', 'rows': 0}
        )
        if verify_response.status_code == 200:
            result = verify_response.json()
            num_found = result.get('response', {}).get('numFound', 0)
            print(f"✅ Solr collection now contains {num_found} documents")
        else:
            print(f"⚠️  Could not verify: {verify_response.status_code}")
    except Exception as e:
        print(f"⚠️  Could not verify insertion: {e}")

if __name__ == "__main__":
    main()


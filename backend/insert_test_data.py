"""Script to insert test data into tax_documents and tax_chunks collections."""

import sys
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.solr_service import get_solr_service
from app.services.embedding_service import get_embedding_service
from app.services.document_service import get_document_service
from app.services.chunk_service import get_chunk_service
from app.models.document import DocumentCreate, GovernanceStateUpdate
from app.models.chunk import ChunkCreate
from app.models.common import GovernanceState

load_dotenv()


def insert_test_data():
    """Insert test documents and chunks into Solr collections."""
    
    print("=" * 60)
    print("Inserting Test Data into Tax KB Collections")
    print("=" * 60)
    
    # Initialize services
    solr = get_solr_service()
    embedding_service = get_embedding_service()
    document_service = get_document_service()
    chunk_service = get_chunk_service()
    
    # Check Solr connection
    print("\n1. Checking Solr connection...")
    health = solr.health_check()
    if not health.get("documents"):
        print("❌ tax_documents collection is not available")
        return False
    if not health.get("chunks"):
        print("❌ tax_chunks collection is not available")
        return False
    print("✅ Both collections are available")
    
    # Test documents data
    test_documents = [
        {
            "name": "IRS_Publication_946_2024.pdf",
            "title": "Section 179 Deduction",
            "description": "Guide to Section 179 business equipment deduction",
            "source_url": "https://www.irs.gov/pub/irs-pdf/p946.pdf",
            "source_domain": "irs.gov",
            "tags": ["business", "deduction", "equipment"],
            "category": "Business Tax",
            "doc_type": "publication",
            "tax_year": 2024,
            "tax_type": "income",
            "jurisdiction": "federal",
            "authority_level": 1,
            "authority_level_rationale": "IRS Publication - highest authority",
            "chunks": [
                "Section 179 allows businesses to deduct the full purchase price of qualifying equipment and software purchased or financed during the tax year. This deduction can significantly reduce taxable income.",
                "To qualify for Section 179, the property must be tangible personal property used in a trade or business. This includes machinery, equipment, vehicles, computers, and furniture.",
                "The maximum Section 179 deduction for 2024 is $1,160,000. This limit is reduced dollar-for-dollar when total qualifying property exceeds $2,890,000."
            ]
        },
        {
            "name": "Form_1040_Instructions_2024.pdf",
            "title": "Standard Deduction 2024",
            "description": "Standard deduction amounts for tax year 2024",
            "source_url": "https://www.irs.gov/pub/irs-pdf/i1040gi.pdf",
            "source_domain": "irs.gov",
            "tags": ["individual", "deduction", "filing"],
            "category": "Individual Tax",
            "doc_type": "instructions",
            "tax_year": 2024,
            "tax_type": "income",
            "jurisdiction": "federal",
            "authority_level": 1,
            "chunks": [
                "The standard deduction for married couples filing jointly is $29,200 for tax year 2024. For single taxpayers and married individuals filing separately, it is $14,600.",
                "For heads of households, the standard deduction is $21,900 for tax year 2024. These amounts are adjusted annually for inflation.",
                "Taxpayers can choose between taking the standard deduction or itemizing deductions, whichever provides the greater tax benefit."
            ]
        },
        {
            "name": "IRS_Publication_544_2024.pdf",
            "title": "Capital Gains Tax",
            "description": "Guide to capital gains and losses",
            "source_url": "https://www.irs.gov/pub/irs-pdf/p544.pdf",
            "source_domain": "irs.gov",
            "tags": ["capital-gains", "investment", "tax-rates"],
            "category": "Investment Tax",
            "doc_type": "publication",
            "tax_year": 2024,
            "tax_type": "income",
            "jurisdiction": "federal",
            "authority_level": 1,
            "chunks": [
                "Long-term capital gains are taxed at 0%, 15%, or 20% depending on your taxable income and filing status. Short-term capital gains are taxed as ordinary income.",
                "Assets held for more than one year qualify for long-term capital gains treatment. Assets held for one year or less are considered short-term.",
                "The 0% rate applies to taxpayers in the 10% or 12% ordinary income tax brackets. The 15% rate applies to those in the 22%, 24%, 32%, or 35% brackets. The 20% rate applies to those in the 37% bracket."
            ]
        },
        {
            "name": "IRS_Publication_587_2024.pdf",
            "title": "Home Office Deduction",
            "description": "Business use of your home",
            "source_url": "https://www.irs.gov/pub/irs-pdf/p587.pdf",
            "source_domain": "irs.gov",
            "tags": ["business", "home-office", "deduction"],
            "category": "Business Tax",
            "doc_type": "publication",
            "tax_year": 2024,
            "tax_type": "income",
            "jurisdiction": "federal",
            "authority_level": 1,
            "chunks": [
                "If you use part of your home exclusively and regularly for business, you may be able to deduct expenses like mortgage interest, insurance, utilities, repairs, and depreciation.",
                "The home office must be used exclusively for business purposes and be your principal place of business or a place where you meet with clients.",
                "You can use either the simplified method ($5 per square foot, up to 300 square feet) or the actual expense method to calculate your home office deduction."
            ]
        },
        {
            "name": "IRS_Publication_590_2024.pdf",
            "title": "Retirement Contributions",
            "description": "Individual Retirement Arrangements (IRAs)",
            "source_url": "https://www.irs.gov/pub/irs-pdf/p590a.pdf",
            "source_domain": "irs.gov",
            "tags": ["retirement", "ira", "401k", "deduction"],
            "category": "Retirement Tax",
            "doc_type": "publication",
            "tax_year": 2024,
            "tax_type": "income",
            "jurisdiction": "federal",
            "authority_level": 1,
            "chunks": [
                "Contributions to traditional IRAs and 401(k) plans can reduce your taxable income. For 2024, the contribution limit for 401(k) plans is $23,000, with an additional $7,500 catch-up contribution for those 50 and older.",
                "Traditional IRA contribution limits for 2024 are $7,000, with an additional $1,000 catch-up contribution for those 50 and older. Roth IRA contributions have the same limits but are made with after-tax dollars.",
                "Contributions to traditional IRAs may be tax-deductible depending on your income, filing status, and whether you or your spouse are covered by a retirement plan at work."
            ]
        },
        {
            "name": "NY_Tax_Guide_2024.pdf",
            "title": "New York State Income Tax Rates",
            "description": "New York State income tax information",
            "source_url": "https://www.tax.ny.gov/pit/file/",
            "source_domain": "tax.ny.gov",
            "tags": ["state", "new-york", "income-tax"],
            "category": "State Tax",
            "doc_type": "publication",
            "tax_year": 2024,
            "tax_type": "income",
            "jurisdiction": "state",
            "state": "NY",
            "authority_level": 2,
            "chunks": [
                "New York State has a progressive income tax system with rates ranging from 4% to 10.9% depending on income level and filing status. The tax applies to New York source income for residents and non-residents.",
                "New York residents are taxed on all income regardless of source. Non-residents are taxed only on New York source income, which includes wages earned in New York and income from New York businesses.",
                "New York City residents may also be subject to city income tax in addition to state income tax. The city tax rates range from 3.078% to 3.876%."
            ]
        },
        {
            "name": "CA_Sales_Tax_Guide_2024.pdf",
            "title": "California Sales Tax Guide",
            "description": "California sales and use tax information",
            "source_url": "https://www.cdtfa.ca.gov/taxes-and-fees/",
            "source_domain": "cdtfa.ca.gov",
            "tags": ["state", "california", "sales-tax"],
            "category": "Sales Tax",
            "doc_type": "publication",
            "tax_year": 2024,
            "tax_type": "sales",
            "jurisdiction": "state",
            "state": "CA",
            "authority_level": 2,
            "chunks": [
                "California's statewide sales tax rate is 7.25%. Local jurisdictions can add additional taxes, making the total rate vary by location. Most goods and services are subject to sales tax, with some exemptions.",
                "Common exemptions from California sales tax include most food products, prescription medications, and certain medical devices. Services are generally not subject to sales tax unless specifically included.",
                "Businesses making sales in California must register with the California Department of Tax and Fee Administration and collect sales tax on taxable transactions."
            ]
        }
    ]
    
    # Insert documents and chunks
    print("\n2. Inserting documents and chunks...")
    
    inserted_docs = 0
    inserted_chunks = 0
    
    for doc_data in test_documents:
        try:
            # Extract chunks
            chunks_data = doc_data.pop("chunks", [])
            
            # Create document
            doc_create = DocumentCreate(**doc_data)
            document = document_service.create_document(doc_create)
            inserted_docs += 1
            print(f"  ✅ Created document: {document.name}")
            
            # Update governance state to Published
            update = GovernanceStateUpdate(
                governance_state=GovernanceState.PUBLISHED,
                changed_by="system",
                reason="Initial publication"
            )
            document = document_service.update_governance_state(document.id, update)
            print(f"  ✅ Updated governance state to Published")
            
            # Create chunks for this document
            for idx, chunk_content in enumerate(chunks_data):
                try:
                    # Generate embedding
                    vector = embedding_service.generate_embedding(chunk_content)
                    
                    # Create chunk with denormalized fields
                    chunk_create = ChunkCreate(
                        content=chunk_content,
                        document_id=document.id,
                        chunk_index=idx,
                        document_name=document.name,
                        title=document.title,
                        source_url=document.source_url,
                        source_domain=document.source_domain,
                        category=document.category,
                        doc_type=document.doc_type,
                        tax_year=document.tax_year,
                        tax_type=document.tax_type,
                        jurisdiction=document.jurisdiction,
                        state=document.state,
                        authority_level=document.authority_level,
                        governance_state=document.governance_state,
                        is_latest_for_tax_year=document.is_latest_for_tax_year,
                        vector=vector,
                    )
                    
                    chunk = chunk_service.create_chunk(chunk_create, generate_embedding=False)
                    inserted_chunks += 1
                    print(f"    ✓ Created chunk {idx + 1}/{len(chunks_data)}")
                    
                except Exception as e:
                    print(f"    ❌ Error creating chunk {idx + 1}: {e}")
                    continue
            
        except Exception as e:
            print(f"  ❌ Error creating document '{doc_data.get('name', 'unknown')}': {e}")
            continue
    
    # Update document chunk counts
    print("\n3. Updating document chunk counts...")
    for doc_data in test_documents:
        try:
            # Find document by name
            docs, _ = document_service.list_documents(
                query=f"name:{doc_data['name']}",
                limit=1
            )
            if docs:
                doc = docs[0]
                # Get chunk count
                chunks, count = chunk_service.list_chunks(
                    document_id=doc.id,
                    limit=1000
                )
                # Update document
                from app.models.document import DocumentUpdate
                document_service.update_document(
                    doc.id,
                    DocumentUpdate()  # Will update chunkCount via service
                )
        except Exception as e:
            print(f"  ⚠️  Could not update chunk count: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("Insertion Summary")
    print("=" * 60)
    print(f"Documents inserted: {inserted_docs}/{len(test_documents)}")
    print(f"Chunks inserted: {inserted_chunks}")
    print("=" * 60)
    
    # Verify
    print("\n4. Verifying data...")
    try:
        docs, doc_count = document_service.list_documents(limit=100)
        chunks, chunk_count = chunk_service.list_chunks(limit=100)
        
        print(f"✅ Total documents in collection: {doc_count}")
        print(f"✅ Total chunks in collection: {chunk_count}")
    except Exception as e:
        print(f"⚠️  Could not verify: {e}")
    
    return True


if __name__ == "__main__":
    try:
        success = insert_test_data()
        if success:
            print("\n🎉 Test data insertion completed!")
            print("\nYou can now test the search API with:")
            print("  POST http://localhost:8000/api/search/rag")
            print("  Body: {\"query\": \"What are the standard deduction amounts?\"}")
        else:
            print("\n❌ Test data insertion failed")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
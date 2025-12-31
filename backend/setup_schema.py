import requests
import json
import sys

base_url = "http://localhost:8983/solr/tax_docs_v2"

def check_collection_exists():
    """Check if the collection exists"""
    try:
        response = requests.get(f"http://localhost:8983/solr/admin/collections?action=LIST")
        if response.status_code == 200:
            collections = response.json().get("collections", [])
            if "tax_docs" in collections:
                print("✅ Collection 'tax_docs' exists")
                return True
            else:
                print("❌ Collection 'tax_docs' does not exist. Please create it first.")
                print("   You can create it using: bin/solr create -c tax_docs")
                return False
        else:
            print(f"⚠️  Could not verify collection existence: {response.status_code}")
            return True  # Continue anyway
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Solr. Please ensure Solr is running on http://localhost:8983")
        return False
    except Exception as e:
        print(f"⚠️  Error checking collection: {e}")
        return True  # Continue anyway

def add_field_type(name, field_type_config):
    """Helper function to add a field type"""
    try:
        payload = {"add-field-type": field_type_config}
        response = requests.post(f"{base_url}/schema", json=payload)
        if response.status_code == 200:
            print(f"✅ Field type '{name}' added: {response.status_code}")
        else:
            print(f"❌ Failed to add field type '{name}': {response.status_code} - {response.text}")
        return response
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection error while adding field type '{name}'")
        return None
    except Exception as e:
        print(f"❌ Error adding field type '{name}': {e}")
        return None

def add_field(name, field_config):
    """Helper function to add a field"""
    try:
        payload = {"add-field": field_config}
        response = requests.post(f"{base_url}/schema", json=payload)
        if response.status_code == 200:
            print(f"✅ Field '{name}' added: {response.status_code}")
        else:
            # Field might already exist, check if it's a duplicate error
            if "already exists" in response.text.lower() or response.status_code == 400:
                print(f"⚠️  Field '{name}' may already exist: {response.status_code}")
            else:
                print(f"❌ Failed to add field '{name}': {response.status_code} - {response.text}")
        return response
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection error while adding field '{name}'")
        return None
    except Exception as e:
        print(f"❌ Error adding field '{name}': {e}")
        return None

def add_copy_field(source, dest):
    """Helper function to add a copy field"""
    try:
        payload = {"add-copy-field": {"source": source, "dest": dest}}
        response = requests.post(f"{base_url}/schema", json=payload)
        if response.status_code == 200:
            print(f"✅ Copy field '{source}' -> '{dest}' added: {response.status_code}")
        else:
            print(f"❌ Failed to add copy field '{source}' -> '{dest}': {response.status_code} - {response.text}")
        return response
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection error while adding copy field '{source}' -> '{dest}'")
        return None
    except Exception as e:
        print(f"❌ Error adding copy field '{source}' -> '{dest}': {e}")
        return None

print("🚀 Starting Solr 9 schema setup for tax_docs collection...\n")

# Check if collection exists
if not check_collection_exists():
    print("\n❌ Exiting. Please create the collection first.")
    sys.exit(1)

print("\n" + "="*60)
print("Proceeding with schema setup...")
print("="*60 + "\n")

# 1. Add dense vector field type (1536 dimensions for embeddings)
print("1. Adding dense vector field type...")
field_type = {
    "name": "knn_vector",
    "class": "solr.DenseVectorField",
    "vectorDimension": 1536,
    "similarityFunction": "cosine"
}
add_field_type("knn_vector", field_type)

# 2. Add vector field for embeddings
print("\n2. Adding vector field...")
vector_field = {
    "name": "vector",
    "type": "knn_vector",
    "indexed": True,
    "stored": True
}
add_field("vector", vector_field)

# 3. Add content field (main text content)
print("\n3. Adding content field...")
content_field = {
    "name": "content",
    "type": "text_general",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("content", content_field)

# 4. Add title field
print("\n4. Adding title field...")
title_field = {
    "name": "title",
    "type": "text_general",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("title", title_field)

# 5. Add chunkId field
print("\n5. Adding chunkId field...")
chunk_id_field = {
    "name": "chunkId",
    "type": "string",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("chunkId", chunk_id_field)

# 6. Add documentName field
print("\n6. Adding documentName field...")
document_name_field = {
    "name": "documentName",
    "type": "text_general",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("documentName", document_name_field)

# 7. Add sourceUrl field
print("\n7. Adding sourceUrl field...")
source_url_field = {
    "name": "sourceUrl",
    "type": "string",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("sourceUrl", source_url_field)

# 8. Add sourceDomain field
print("\n8. Adding sourceDomain field...")
source_domain_field = {
    "name": "sourceDomain",
    "type": "string",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("sourceDomain", source_domain_field)

# 9. Add category field
print("\n9. Adding category field...")
category_field = {
    "name": "category",
    "type": "string",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("category", category_field)

# 10. Add jurisdiction field
print("\n10. Adding jurisdiction field...")
jurisdiction_field = {
    "name": "jurisdiction",
    "type": "string",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("jurisdiction", jurisdiction_field)

# 11. Add state field
print("\n11. Adding state field...")
state_field = {
    "name": "state",
    "type": "string",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("state", state_field)

# 12. Add taxYear field
print("\n12. Adding taxYear field...")
tax_year_field = {
    "name": "taxYear",
    "type": "pint",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("taxYear", tax_year_field)

# 13. Add effectiveFrom field (date)
print("\n13. Adding effectiveFrom field...")
effective_from_field = {
    "name": "effectiveFrom",
    "type": "pdate",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("effectiveFrom", effective_from_field)

# 14. Add effectiveTo field (date)
print("\n14. Adding effectiveTo field...")
effective_to_field = {
    "name": "effectiveTo",
    "type": "pdate",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("effectiveTo", effective_to_field)

# 15. Add appliesToTaxYears field (multi-valued integers)
print("\n15. Adding appliesToTaxYears field...")
applies_to_tax_years_field = {
    "name": "appliesToTaxYears",
    "type": "pint",
    "indexed": True,
    "stored": True,
    "multiValued": True
}
add_field("appliesToTaxYears", applies_to_tax_years_field)

# 16. Add appliesToJurisdictions field (multi-valued strings)
print("\n16. Adding appliesToJurisdictions field...")
applies_to_jurisdictions_field = {
    "name": "appliesToJurisdictions",
    "type": "string",
    "indexed": True,
    "stored": True,
    "multiValued": True
}
add_field("appliesToJurisdictions", applies_to_jurisdictions_field)

# 17. Add authorityLevel field
print("\n17. Adding authorityLevel field...")
authority_level_field = {
    "name": "authorityLevel",
    "type": "pint",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("authorityLevel", authority_level_field)

# 18. Add authorityLevelRationale field
print("\n18. Adding authorityLevelRationale field...")
authority_level_rationale_field = {
    "name": "authorityLevelRationale",
    "type": "text_general",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("authorityLevelRationale", authority_level_rationale_field)

# 19. Add docType field
print("\n19. Adding docType field...")
doc_type_field = {
    "name": "docType",
    "type": "string",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("docType", doc_type_field)

# 20. Add formFamily field
print("\n20. Adding formFamily field...")
form_family_field = {
    "name": "formFamily",
    "type": "string",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("formFamily", form_family_field)

# 21. Add version field
print("\n21. Adding version field...")
version_field = {
    "name": "version",
    "type": "string",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("version", version_field)

# 22. Add fileVersion field
print("\n22. Adding fileVersion field...")
file_version_field = {
    "name": "fileVersion",
    "type": "string",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("fileVersion", file_version_field)

# 23. Add revisionDate field (date)
print("\n23. Adding revisionDate field...")
revision_date_field = {
    "name": "revisionDate",
    "type": "pdate",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("revisionDate", revision_date_field)

# 24. Add paragraphNumber field
print("\n24. Adding paragraphNumber field...")
paragraph_number_field = {
    "name": "paragraphNumber",
    "type": "pint",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("paragraphNumber", paragraph_number_field)

# 25. Add priorityRank field
print("\n25. Adding priorityRank field...")
priority_rank_field = {
    "name": "priorityRank",
    "type": "pint",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("priorityRank", priority_rank_field)

# 26. Add relevanceScore field (float)
print("\n26. Adding relevanceScore field...")
relevance_score_field = {
    "name": "relevanceScore",
    "type": "pfloat",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("relevanceScore", relevance_score_field)

# 27. Add isPreferred field (boolean)
print("\n27. Adding isPreferred field...")
is_preferred_field = {
    "name": "isPreferred",
    "type": "boolean",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("isPreferred", is_preferred_field)

# 28. Add conflictResolutionReason field
print("\n28. Adding conflictResolutionReason field...")
conflict_resolution_reason_field = {
    "name": "conflictResolutionReason",
    "type": "string",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("conflictResolutionReason", conflict_resolution_reason_field)

# 29. Add replacedBy field
print("\n29. Adding replacedBy field...")
replaced_by_field = {
    "name": "replacedBy",
    "type": "string",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("replacedBy", replaced_by_field)

# 30. Add supersededBy field
print("\n30. Adding supersededBy field...")
superseded_by_field = {
    "name": "supersededBy",
    "type": "string",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("supersededBy", superseded_by_field)

# 31. Add supersededByVersionId field
print("\n31. Adding supersededByVersionId field...")
superseded_by_version_id_field = {
    "name": "supersededByVersionId",
    "type": "string",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("supersededByVersionId", superseded_by_version_id_field)

# 32. Add hasNewerVersion field (boolean)
print("\n32. Adding hasNewerVersion field...")
has_newer_version_field = {
    "name": "hasNewerVersion",
    "type": "boolean",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("hasNewerVersion", has_newer_version_field)

# 33. Add isLatestForTaxYear field (boolean)
print("\n33. Adding isLatestForTaxYear field...")
is_latest_for_tax_year_field = {
    "name": "isLatestForTaxYear",
    "type": "boolean",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("isLatestForTaxYear", is_latest_for_tax_year_field)

# 34. Add lastCrawled field (date)
print("\n34. Adding lastCrawled field...")
last_crawled_field = {
    "name": "lastCrawled",
    "type": "pdate",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("lastCrawled", last_crawled_field)

# 35. Add lastEmbedded field (date)
print("\n35. Adding lastEmbedded field...")
last_embedded_field = {
    "name": "lastEmbedded",
    "type": "pdate",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("lastEmbedded", last_embedded_field)

# 36. Add chunkCount field
print("\n36. Adding chunkCount field...")
chunk_count_field = {
    "name": "chunkCount",
    "type": "pint",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("chunkCount", chunk_count_field)

# 37. Add tokensIndexed field
print("\n37. Adding tokensIndexed field...")
tokens_indexed_field = {
    "name": "tokensIndexed",
    "type": "plong",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("tokensIndexed", tokens_indexed_field)

# 38. Add embeddingModel field
print("\n38. Adding embeddingModel field...")
embedding_model_field = {
    "name": "embeddingModel",
    "type": "string",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("embeddingModel", embedding_model_field)

# 39. Add parsingQuality field
print("\n39. Adding parsingQuality field...")
parsing_quality_field = {
    "name": "parsingQuality",
    "type": "string",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("parsingQuality", parsing_quality_field)

# 40. Add classificationConfidence field (float)
print("\n40. Adding classificationConfidence field...")
classification_confidence_field = {
    "name": "classificationConfidence",
    "type": "pfloat",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("classificationConfidence", classification_confidence_field)

# 41. Add needsHumanReview field (boolean)
print("\n41. Adding needsHumanReview field...")
needs_human_review_field = {
    "name": "needsHumanReview",
    "type": "boolean",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("needsHumanReview", needs_human_review_field)

# 42. Add reviewReason field
print("\n42. Adding reviewReason field...")
review_reason_field = {
    "name": "reviewReason",
    "type": "text_general",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("reviewReason", review_reason_field)

# 43. Add reviewedAt field (date)
print("\n43. Adding reviewedAt field...")
reviewed_at_field = {
    "name": "reviewedAt",
    "type": "pdate",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("reviewedAt", reviewed_at_field)

# 44. Add reviewedBy field
print("\n44. Adding reviewedBy field...")
reviewed_by_field = {
    "name": "reviewedBy",
    "type": "string",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("reviewedBy", reviewed_by_field)

# 45. Add governanceState field
print("\n45. Adding governanceState field...")
governance_state_field = {
    "name": "governanceState",
    "type": "string",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("governanceState", governance_state_field)

# 46. Add excerpt field
print("\n46. Adding excerpt field...")
excerpt_field = {
    "name": "excerpt",
    "type": "text_general",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("excerpt", excerpt_field)

# 47. Add url field (for SourceDocument)
print("\n47. Adding url field...")
url_field = {
    "name": "url",
    "type": "string",
    "indexed": True,
    "stored": True,
    "multiValued": False
}
add_field("url", url_field)

# 48. Add supersessionChain field (multi-valued strings)
print("\n48. Adding supersessionChain field...")
supersession_chain_field = {
    "name": "supersessionChain",
    "type": "string",
    "indexed": True,
    "stored": True,
    "multiValued": True
}
add_field("supersessionChain", supersession_chain_field)

print("\n" + "="*60)
print("🎉 Schema setup complete!")
print("="*60)
print("\nAll fields have been added to the tax_docs collection.")
print("You can now start indexing your tax documents!")


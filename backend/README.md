EverLeagues – Federal & Multi-State Tax Corpus Ingestion + RAG System Developer Requirements (With Source URLs)

This version adds **official source URLs** for all federal and state data locations.

======================================================
SECTION 1 — GOALS & NON-GOALS
======================================================

Objectives:
- Build a canonical federal + multi-state tax knowledge corpus fully stored locally.
- Support RAG, semantic search, and advanced agentic tax workflows (returns, audit, sales tax).
- Enable daily update cycles for corpus freshness.
- Preserve strong provenance and citations.

Non-goals:
- No commercial publishers (Lexis/CCH/Thomson/Bloomberg).
- No scraping sources with usage restrictions unless approved by Legal.


======================================================
SECTION 2 — HIGH-LEVEL ARCHITECTURE
======================================================

Components:
- Source Fetchers
- Ingestion & Normalization Pipeline
- Chunking & Embedding
- Solr 9 Indexing (text + vector)
- Daily Update Scheduler
- RAG Retrieval API


======================================================
SECTION 3 — FEDERAL CORPUS REQUIREMENTS + URLs
======================================================

-------------------------
3.1 Internal Revenue Code
-------------------------
Primary Sources:
- **OLRC (Office of Law Revision Counsel)** – Title 26 XML  
  https://uscode.house.gov/download/download.shtml  
- US Code Title 26 (HTML browser view):  
  https://uscode.house.gov/view.xhtml?path=/prelim@title26  
- **GovInfo** – US Code annual editions  
  https://www.govinfo.gov/app/collection/USCODE

-------------------------
3.2 IRS Regulations (CFR Title 26)
-------------------------
Primary Sources:
- **GovInfo – CFR Bulk Data (XML)**  
  https://www.govinfo.gov/bulkdata/CFR  
- CFR Title 26 (HTML/PDF):  
  https://www.govinfo.gov/app/collection/cfr/2024/title26  
- **eCFR (current, unofficial)**  
  https://www.ecfr.gov/title-26

-------------------------
3.3 IRS Publications
-------------------------
Sources:
- IRS Publications index:  
  https://www.irs.gov/forms-pubs  
- Direct PDF downloads (Static Files Directory):  
  https://www.irs.gov/pub/irs-pdf/  (individual PDFs)

Example:
- Pub 17: https://www.irs.gov/publications/p17

-------------------------
3.4 IRS Forms & Instructions (Last 8 Years)
-------------------------
Sources:
- Main forms search:  
  https://www.irs.gov/forms-instructions  
- Prior-year forms:  
  https://www.irs.gov/forms-pubs/prior-year  
- Direct form PDFs:  
  https://www.irs.gov/pub/irs-pdf/

Examples:
- Form 1040: https://www.irs.gov/forms-pubs/about-form-1040  
- Instructions 1040: https://www.irs.gov/forms-pubs/about-publication-501

-------------------------
3.5 IRS FAQs
-------------------------
Source:
- IRS FAQ index:  
  https://www.irs.gov/faqs


======================================================
SECTION 4 — MULTI-STATE TAX CORPUS + URLs
======================================================

States: NY, CA, NJ, CT, MA, PA

Metadata:
- jurisdiction_level = state
- state = NY/CA/NJ/CT/MA/PA
- authority_level = statute/regulation/bulletin/notice/ruling/publication


-------------------------
4.1 New York (NY)
-------------------------
Statutes:
- NY State Senate – Tax Law:  
  https://www.nysenate.gov/legislation/laws/TAX

Department of Taxation & Finance:
- Publications:  
  https://www.tax.ny.gov/pubs_and_bulls/pubs_and_bulletins.htm
- Sales Tax Bulletins:  
  https://www.tax.ny.gov/pubs_and_bulls/tg_bulletins/st/

-------------------------
4.2 California (CA)
-------------------------
Statutes:
- CA Legislative Information – Revenue & Taxation Code:  
  https://leginfo.legislature.ca.gov/faces/codes.xhtml

Administrative Guidance:
- CA Department of Tax and Fee Administration (CDTFA):  
  https://www.cdtfa.ca.gov/
- Sales & Use Tax Law Guides:  
  https://www.cdtfa.ca.gov/lawguides/vol1/sutl/sales-and-use-tax-law-guide.html

-------------------------
4.3 New Jersey (NJ)
-------------------------
Taxation Dept:
- NJ Division of Taxation – Technical Bulletins:  
  https://www.state.nj.us/treasury/taxation/tech.shtml  
- Publications & Guidance:  
  https://www.state.nj.us/treasury/taxation/pubs.shtml

-------------------------
4.4 Connecticut (CT)
-------------------------
CT Department of Revenue Services:
- Publications:  
  https://portal.ct.gov/DRS/Publications/Publications  
- Policy Statements & Special Notices:  
  https://portal.ct.gov/DRS/Publications/Policy-Statements

-------------------------
4.5 Massachusetts (MA)
-------------------------
MA Department of Revenue:
- Technical Information Releases (TIRs):  
  https://www.mass.gov/info-details/technical-information-releases  
- Directives & Guidance:  
  https://www.mass.gov/info-details/directives

-------------------------
4.6 Pennsylvania (PA)
-------------------------
PA Department of Revenue:
- Tax Bulletins:  
  https://www.revenue.pa.gov/FormsandPublications/Pages/Tax-Bulletins.aspx  
- Notices & Policies:  
  https://www.revenue.pa.gov/FormsandPublications/Pages/default.aspx  
- PA Code (Title 61 – Revenue):  
  https://www.pacodeandbulletin.gov/Display/pacode?file=/secure/pacode/data/061/061toc.html


======================================================
SECTION 5 — SALES & USE TAX SUB-CORPUS
======================================================

Each state includes:
- Sales & Use tax statutes (where allowed)
- Regulations
- Sales tax bulletins / notices
- Sales tax forms & instructions (8 years)

Metadata:
- tax_type = sales_use
- sales_tax_subtopic = nexus/sourcing/exemptions/marketplace/etc.


======================================================
SECTION 6 — NORMALIZATION PIPELINE
======================================================

Raw storage:
- tax/raw/{federal|state}/{doc_type}/{year}/file.xxx

Normalized JSON:
- tax/normalized/{state}/{type}/{id}.json

Fields:
- doc_id
- jurisdiction_level
- state
- doc_type
- authority_level
- title
- citation/section
- year
- version_tag
- source_url
- retrieved_at
- text
- structure


======================================================
SECTION 7 — CHUNKING & INDEXING (SOLR 9)
======================================================

Chunk sizes:
- IRC/CFR: 400–800 tokens
- Pubs: section-based
- Forms instructions: line groups
- Sales tax: smaller chunks (300–600 tokens)

Solr fields:
- id
- doc_id
- jurisdiction_level
- state
- doc_type
- authority_level
- tax_type
- text
- embedding
- source_url
- version_tag
- is_current


======================================================
SECTION 8 — DAILY UPDATE MECHANISM
======================================================

Scheduler:
- check_updates_irs
- check_updates_irc
- check_updates_cfr
- check_updates_state_{NY,CA,NJ,CT,MA,PA}

Comparators:
- Last-Modified / ETag
- Hashing of downloaded documents
- New items in bulletin/publication lists

On update:
- Re-ingest → re-normalize → re-chunk → re-embed → Solr upsert


======================================================
SECTION 9 — RAG RETRIEVAL LAYER
======================================================

Requirements:
- Solr hybrid (lexical + vector)
- Filters for:
  - state
  - jurisdiction_level
  - tax_type
  - doc_type


======================================================
SECTION 10 — LICENSING & COMPLIANCE
======================================================

Federal:
- IRS content is public domain.

State:
- Must review TOU for:
  - Statutory sources
  - Code compilations
- Use only official gov websites.
- No scraping commercial publishers.




EverLeagues Tax Corpus Ingestion and RAG System - Proof of Concept (POC) Document 
Project Goal: To build a foundational, locally-stored, canonical knowledge corpus of federal and multi-state tax law and guidance, integrated with a Retrieval-Augmented Generation (RAG) system for advanced tax workflows. 
POC Timeline: 1.5 Months (6 Weeks) 
1. Project Deliverables 
The Proof of Concept (POC) will focus on establishing the core ingestion pipeline, indexing mechanism, and a functional RAG retrieval layer for a defined subset of the required data sources.
Deliverable ID	Deliverable 	Description 	Status
D1	Core Ingestion 
Pipeline	A robust, containerized pipeline capable of fetching, normalizing, and storing raw data from the selected Federal and State sources.	Complete
D2	Normalized Data Schema	A finalized JSON schema (Section 6) implemented for the normalized tax corpus, including all required metadata fields (e.g., doc_id , 
jurisdiction_level , source_url ).	Complete
D3 	Solr 9 Index Setup	A fully configured Solr 9 instance with a schema supporting both text and vector indexing, including all required filter fields (Section 7).	Complete
D4	Initial Corpus 
Load	Successful ingestion and indexing of the Federal Corpus Subset (IRC, CFR Title 26) and One State Corpus (e.g., New York - NY) to demonstrate end-to-end functionality.	Complete
D5 	RAG Retrieval API	A RESTful API endpoint that accepts a query and returns relevant text chunks from the Solr index using a hybrid (lexical + vector) search strategy (Section 9).	Complete


           2. Project Development Plan (6 Week) 
The development plan is structured into three two-week sprints, focusing on establishing the core infrastructure, implementing the ingestion and indexing, and finally, integrating the RAG retrieval layer and update prototype. 
Week 	Phase Focus 	Key Activities	Deliverables Targeted
W1- 
W2	Infrastructure & Core Pipeline Setup	- Finalize technology stack and set up 
development environment (Solr 9, Python environment). - Design and implement the Source Fetcher for the Federal Corpus Subset (IRC XML, CFR XML). - Define and implement the Normalization Pipeline and the Normalized Data Schema (D2). - Set up and configure the Solr 9 Index (D3) with text and vector fields.	D1 (Partial), 
D2, D3
W3- 
W4	Corpus 
Ingestion & 
Indexing	- Implement Chunking & Embedding logic for the Federal Corpus Subset. - Execute the Initial Corpus Load (D4) for the Federal Subset and one State (NY). - Implement the Source Fetcher for the selected State Corpus (NY 
Statutes/Publications). - Develop initial QA scripts to validate data integrity and metadata accuracy.	D1, D4, QA 
(Partial)
W5- 
W6	RAG 
Integration & 
Update 
Prototype	- Implement the RAG Retrieval API (D5), integrating hybrid search (lexical + vector) with Solr. - Implement required RAG filters (jurisdiction_level,state, doc_type, tax_type).	D5


3. Quality Assurance (QA) Strategy 
The QA process will be integrated, focusing on data integrity, system performance, and functional correctness of the RAG retrieval.
QA Area 	Focus 	Key Metrics / Checks
Data 
Integrity	Ensuring the 
corpus is 
accurate and 
complete.	- Metadata Validation: Verify all normalized documents contain correct jurisdiction_level , doc_type , and source_url . - Completeness Check: Confirm all documents from the selected subset sources are successfully ingested. - Provenance Check: Ensure the source_url and retrieved_at fields are correctly populated for every document.
Ingestion 
Pipeline	Testing the 
reliability and 
efficiency of the pipeline.	- Idempotency: Verify re-running the ingestion process does not create duplicate entries. - Error Handling: Test the pipeline’s ability to handle malformed source files or network errors gracefully. - Normalization Accuracy: Spot-check raw vs. normalized content to ensure no data loss or corruption.
RAG 
Retrieval	Validating the 
effectiveness of the search 
mechanism.	- Hybrid Search Test: Verify that queries utilize both lexical (text) and vector (semantic) search. - Filter Accuracy: Test all implemented filters ( state , 
doc_type , etc.) to ensure they correctly narrow the search results. - Relevance Scoring: Manually evaluate the top-K results for a set of sample tax queries to confirm high relevance.


4. Architecture Diagram 
The system architecture is designed around a modular, scalable pipeline for a static initial corpus, supporting advanced RAG capabilities. 
Components: 
1. Source Layer: Official government websites (Federal: OLRC, GovInfo, IRS; State: NY Senate, NY Tax Dept, etc.). 
2. Source Fetchers: Dedicated modules responsible for fetching raw data and storing it in the Raw Storage for the initial load. 
3. Raw Storage: Persistent storage for original, raw source files (e.g., XML, PDF, HTML).
4. Ingestion & Normalization Pipeline: Processes raw files, extracts text and structure, enriches with metadata, and transforms them into the standardized Normalized JSON format. 
5. Normalized Storage: Persistent storage for clean, structured JSON documents. 
6. Chunking & Embedding: Breaks down normalized documents into smaller, context-rich chunks and generates vector embeddings using a pre-trained model. 
7. Solr 9 Index: The core search engine, storing both the text chunks and their corresponding vector embeddings for hybrid search. 
8. RAG Retrieval API: The external interface, accepting user queries and performing a hybrid search on the Solr index to return the most relevant text chunks (the “Retrieval” part of RAG). 

 


            5. Process Flow Diagram 
The process flow details the sequence of operations from a document update to its availability in the RAG system.
 

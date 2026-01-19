"""Prompt templates for LLM services.

This module contains all the prompts used by the classification and RAG services.
Edit these strings directly to customize the LLM behavior.
"""

# =============================================================================
# DOCUMENT CLASSIFIER PROMPTS
# =============================================================================

CLASSIFIER_SYSTEM_PROMPT = """You are a tax document classification expert. Extract metadata from tax documents accurately.

Analyze tax documents and extract structured metadata including title, description, document type, authority level, tags, and tax year. Always respond with valid JSON only."""


CLASSIFIER_USER_PROMPT_TEMPLATE = """Analyze this tax document and extract the following metadata in JSON format:

Document text (first part):
---
{document_text}
---

Source URL: {source_url}
Filename: {filename}

Please extract and return a JSON object with these fields:
{{
  "title": "Document title (extract from content or derive from filename)",
  "description": "Brief summary of what the document covers (1-2 sentences)",
  "doc_type": "One of: form, instructions, publication, schedule, regulation, ruling, notice, faq, guide, other",
  "authority_level": "Number 1-6 where 1=Statute/Regulation, 2=Forms, 3=Rulings, 4=FAQs, 5=Expert, 6=Other",
  "authority_level_rationale": "Brief explanation of why this authority level",
  "tags": ["array", "of", "relevant", "keywords"] maximum 4,
  "tax_year": "Year as integer if mentioned, null otherwise",
  "form_family": "Form family identifier (e.g. 1040, SchC) if applicable"
}}

Return ONLY the JSON object, no other text."""


# =============================================================================
# RAG ANSWER GENERATION PROMPTS
# =============================================================================

RAG_SYSTEM_PROMPT = """You are an expert tax advisor assistant for a professional tax knowledge base. 
Your role is to provide accurate, helpful answers based ONLY on the retrieved document chunks provided below.

IMPORTANT RULES:
1. Only answer based on the information in the provided chunks. Do not make up information.
2. If the chunks don't contain enough information to fully answer the question, clearly state what you can answer and what information is missing.
3. Always cite your sources using [1], [2], etc. corresponding to the chunk numbers.
4. Be precise and professional in your language.
5. When discussing tax amounts, dates, or specific rules, quote the exact text from the sources.
6. If there are conflicting information between sources, note the conflict and explain which source takes precedence (higher authority level, more recent date, or jurisdiction match).
7. Format your response with clear structure using bullet points or numbered lists when appropriate.
8. Do not provide tax advice - instead, provide information from the knowledge base and recommend consulting a tax professional for specific situations.

AUTHORITY LEVELS (1 = highest authority):
- Level 1: IRC/Treasury Regulations
- Level 2: IRS Forms & Instructions
- Level 3: Revenue Procedures/Rulings
- Level 4: IRS Publications
- Level 5: State Tax Authority
- Level 6: Third-party guidance"""


RAG_USER_PROMPT_TEMPLATE = """Question: {query}

{additional_context}

Retrieved Documents:
{context}

Please provide a comprehensive answer based on the retrieved documents above. 
Remember to cite sources using [1], [2], etc."""


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_classifier_system_prompt() -> str:
    """Get the system prompt for document classification."""
    return CLASSIFIER_SYSTEM_PROMPT


def get_classifier_user_prompt(
    document_text: str,
    source_url: str = None,
    filename: str = None,
) -> str:
    """
    Get the formatted user prompt for document classification.
    
    Args:
        document_text: The document text to classify
        source_url: Optional source URL
        filename: Optional filename
        
    Returns:
        Formatted user prompt
    """
    return CLASSIFIER_USER_PROMPT_TEMPLATE.format(
        document_text=document_text,
        source_url=source_url or "Not provided",
        filename=filename or "Not provided",
    )


def get_rag_system_prompt() -> str:
    """Get the system prompt for RAG answer generation."""
    return RAG_SYSTEM_PROMPT


def get_rag_user_prompt(
    query: str,
    context: str,
    additional_context: str = None,
) -> str:
    """
    Get the formatted user prompt for RAG answer generation.
    
    Args:
        query: The user's question
        context: Formatted retrieved chunks
        additional_context: Optional additional context (e.g., filters)
        
    Returns:
        Formatted user prompt
    """
    context_line = f"Context: {additional_context}\n" if additional_context else ""
    
    return RAG_USER_PROMPT_TEMPLATE.format(
        query=query,
        context=context,
        additional_context=context_line,
    )

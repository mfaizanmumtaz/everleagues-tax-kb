"""LLM Service for generating RAG answers using LangChain and OpenAI."""

from typing import List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from ..config import settings
from ..prompts import get_rag_system_prompt, get_rag_user_prompt


class LLMService:
    """Service for generating answers using LLM based on retrieved chunks."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """
        Initialize the LLM service.

        Args:
            api_key: OpenAI API key (uses settings if not provided)
            model: Model to use (uses settings.rag_llm_model if not provided)
            temperature: Temperature for generation (uses settings if not provided)
            max_tokens: Maximum tokens in the response (uses settings if not provided)
        """
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.rag_llm_model
        self.temperature = temperature if temperature is not None else settings.rag_llm_temperature
        self.max_tokens = max_tokens or settings.rag_llm_max_tokens
        self._client: Optional[ChatOpenAI] = None

    def _get_client(self) -> ChatOpenAI:
        """Lazy load the ChatOpenAI client."""
        if self._client is None:
            if not self.api_key:
                raise RuntimeError(
                    "OpenAI API key is required for answer generation. "
                    "Set OPENAI_API_KEY in your environment."
                )
            try:
                self._client = ChatOpenAI(
                    model=self.model,
                    api_key=self.api_key,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
            except ImportError:
                raise RuntimeError(
                    "langchain-openai is required for answer generation"
                )
        return self._client

    def _format_chunks_for_context(self, chunks: List[dict]) -> str:
        """
        Format retrieved chunks into a context string for the LLM.
        Removes duplicate chunks based on content, keeping only unique ones.

        Args:
            chunks: List of chunk dictionaries with content and metadata

        Returns:
            Formatted context string with numbered chunks
        """
        context_parts = []
        seen_contents = set()

        for chunk in chunks:
            content = chunk.get("content", "")

            # Skip duplicate chunks based on content
            if content in seen_contents:
                continue
            seen_contents.add(content)

            # Build chunk header with metadata
            chunk_number = len(context_parts) + 1
            header_parts = [f"[{chunk_number}]"]

            doc_name = chunk.get("document_name", "Unknown Document")
            header_parts.append(f"Source: {doc_name}")

            if chunk.get("authority_level"):
                header_parts.append(f"Authority Level: {chunk['authority_level']}")

            if chunk.get("tax_year"):
                header_parts.append(f"Tax Year: {chunk['tax_year']}")

            if chunk.get("jurisdiction"):
                jurisdiction = chunk["jurisdiction"]
                if chunk.get("state"):
                    jurisdiction += f" - {chunk['state']}"
                header_parts.append(f"Jurisdiction: {jurisdiction}")

            if chunk.get("effective_from"):
                header_parts.append(f"Effective: {chunk['effective_from']}")

            header = " | ".join(header_parts)

            # Build the chunk text (no truncation)
            chunk_text = f"{header}\n{content}\n"
            context_parts.append(chunk_text)

        return "\n---\n".join(context_parts)

    async def generate_answer(
        self,
        query: str,
        chunks: List[dict],
        additional_context: Optional[str] = None,
        graph_context: Optional[str] = None,
    ) -> str:
        """
        Generate an answer based on retrieved chunks.

        Args:
            query: The user's question
            chunks: List of retrieved chunks with content and metadata
            additional_context: Optional additional context (e.g., filter information)
            graph_context: Optional ontology graph context for traceable citations
                (e.g. "Concepts: WAGES_INCOME (IRC 61); Related forms: W-2, 1040 Line 1z")
        """
        if not chunks:
            return (
                "I couldn't find any relevant documents in the knowledge base to answer your question. "
                "Please try rephrasing your query or adjusting the search filters."
            )

        client = self._get_client()

        # Format chunks into context
        context = self._format_chunks_for_context(chunks)

        # Load prompts from files
        combined_context = []
        if graph_context:
            combined_context.append(
                f"Ontology context (use for traceable Concept -> Authority -> Form citations): {graph_context}"
            )
        if additional_context:
            combined_context.append(additional_context)
        context_str = "\n".join(combined_context) if combined_context else None

        system_prompt = get_rag_system_prompt()
        user_prompt = get_rag_user_prompt(
            query=query,
            context=context,
            additional_context=context_str,
        )

        # Create messages
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        # Generate response
        try:
            response = await client.ainvoke(messages)
            return response.content
        except Exception as e:
            # Return a graceful error message
            return (
                f"I encountered an error while generating the answer: {str(e)}. "
                "The retrieved documents are shown above for your reference."
            )

    def generate_answer_sync(
        self,
        query: str,
        chunks: List[dict],
        additional_context: Optional[str] = None,
        graph_context: Optional[str] = None,
    ) -> str:
        """
        Synchronous version of generate_answer.

        Args:
            query: The user's question
            chunks: List of retrieved chunks with content and metadata
            additional_context: Optional additional context

        Returns:
            Generated answer string with citations
        """
        if not chunks:
            return (
                "I couldn't find any relevant documents in the knowledge base to answer your question. "
                "Please try rephrasing your query or adjusting the search filters."
            )

        client = self._get_client()

        # Format chunks into context
        context = self._format_chunks_for_context(chunks)

        # Load prompts from files
        combined_context = []
        if graph_context:
            combined_context.append(
                f"Ontology context (use for traceable Concept -> Authority -> Form citations): {graph_context}"
            )
        if additional_context:
            combined_context.append(additional_context)
        context_str = "\n".join(combined_context) if combined_context else None

        system_prompt = get_rag_system_prompt()
        user_prompt = get_rag_user_prompt(
            query=query,
            context=context,
            additional_context=context_str,
        )

        # Create messages
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        # Generate response (sync)
        try:
            response = client.invoke(messages)
            return response.content
        except Exception as e:
            return (
                f"I encountered an error while generating the answer: {str(e)}. "
                "The retrieved documents are shown above for your reference."
            )


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service

from typing import Callable, List, Optional

from langchain.agents import Tool
from langchain_core.output_parsers import StrOutputParser
from langchain.prompts import ChatPromptTemplate

from .document_processor import DocumentProcessor


def _format_context_chunks(chunks: List[dict]) -> str:
    # Format context chunks with filenames for agent consumption.
    formatted = []
    for idx, chunk in enumerate(chunks, start=1):
        text = chunk.get("text", "").strip()
        filename = chunk.get("filename") or "unknown source"
        if not text:
            continue
        formatted.append(f"[{idx}] ({filename}) {text}")
    return "\n\n".join(formatted)


def build_tools(
    processor: DocumentProcessor,
    summarizer_llm=None,
    get_last_answer: Optional[Callable[[], Optional[str]]] = None,
) -> List[Tool]:
    # Create LangChain tools for document search and summarization.

    def list_documents(_input: str = "") -> str:
        docs = processor.list_stored_documents()
        if not docs:
            return "No documents available."
        return "\n".join(
            f"- {doc.get('filename', 'unknown')} (uploaded: {doc.get('uploaded_at', 'n/a')})"
            for doc in docs
        )

    def search_documents(query: str, document: Optional[str] = None, limit: int = 10) -> str:
        if not query:
            return "Query is required."
        contexts = processor.get_context(
            question=query,
            specific_document=document,
            return_metadata=True
        )
        if not contexts:
            return "No relevant passages found."
        return _format_context_chunks(contexts[:limit])

    def _run_summarizer(text: str, max_points: int = 5) -> str:
        """Optional summarization helper to condense retrieved passages."""
        cleaned = text.strip()
        if not cleaned:
            return "Nothing to summarize."
        if summarizer_llm is None:
            # Simple fallback so the tool is still usable in tests/offline.
            snippet = cleaned[:500] + ("..." if len(cleaned) > 500 else "")
            bullets = [line.strip() for line in snippet.splitlines() if line.strip()]
            if not bullets:
                bullets = [snippet]
            return "\n".join(f"• {line}" for line in bullets)

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Return concise bullet points only (each starting with •). Keep it factual.",
                ),
                ("user", "Limit to {max_points} bullet points. Text:\n{text}"),
            ]
        )
        chain = prompt | summarizer_llm | StrOutputParser()
        return chain.invoke({"text": cleaned, "max_points": max_points})

    def summarize_text(text: str, max_points: int = 5) -> str:
        return _run_summarizer(text, max_points)

    def summarize_last_answer(max_points: int = 5) -> str:
        if get_last_answer is None:
            return "No previous answer to summarize."
        last = get_last_answer()
        if not last:
            return "No previous answer to summarize."
        return _run_summarizer(last, max_points)

    return [
        Tool(
            name="list_documents",
            func=list_documents,
            description="List available documents for the current user.",
        ),
        Tool(
            name="search_documents",
            func=search_documents,
            description=(
                "Search the user's documents for passages relevant to a query. "
                "Optional: specify a document filename. Returns formatted chunks with sources."
            ),
        ),
        Tool(
            name="summarize_text",
            func=summarize_text,
            description="Summarize provided text into concise bullet points (use after searching documents).",
        ),
        Tool(
            name="summarize_last_answer",
            func=summarize_last_answer,
            description="Summarize the assistant's most recent answer into concise bullet points.",
        ),
    ]

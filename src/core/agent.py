import os
from typing import Optional

from langchain.agents import AgentExecutor
try:
    from langchain.agents import create_openai_functions_agent as _create_agent
except ImportError:  # Fallback for tool-calling helper rename
    from langchain.agents import create_openai_tools_agent as _create_agent  # type: ignore
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory

from .document_processor import DocumentProcessor
from .tools import build_tools


class AgentResponder:
    """LangChain-powered agent that orchestrates tool use for QA."""

    def __init__(
        self,
        processor: DocumentProcessor,
        api_key: Optional[str] = None,
        llm: Optional[ChatOpenAI] = None,
        summarizer_llm: Optional[ChatOpenAI] = None,
        executor: Optional[AgentExecutor] = None,
        last_answer_getter=None,
    ):
        if executor:
            self.processor = processor
            self.llm = llm
            self.tools = build_tools(
                processor=processor,
                summarizer_llm=summarizer_llm or llm,
                get_last_answer=last_answer_getter,
            )
            self.executor = executor
            return

        self.processor = processor
        self.llm = llm or ChatOpenAI(
            # Use a tool-calling capable model
            model="gpt-4o-mini",
            temperature=0.3,
            api_key=api_key or os.environ.get("OPENAI_API_KEY"),
        )

        # Reuse the same chat model for summarization if none is provided.
        self.tools = build_tools(
            processor=processor,
            summarizer_llm=summarizer_llm or self.llm,
            get_last_answer=last_answer_getter,
        )

        # Keep only the most recent turns to control prompt size/cost.
        self.memory = ConversationBufferWindowMemory(
            k=6, return_messages=True, memory_key="chat_history"
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "You are an educational assistant that must ground answers in the user's documents. "
                        "Always call tools to retrieve context before answering. "
                        "For summary requests (summarize, summary, bullet points), first call search_documents; "
                        "if no relevant context is found, say so rather than summarizing unrelated content. "
                        "When summarizing, call summarize_text on the retrieved passages or summarize_last_answer when the user asks to summarize your previous reply. "
                        "For follow-up questions that reference earlier answers (e.g., 'explain that bullet'), use summarize_last_answer to recall what you said and build on it before searching. "
                        "When responding, cite chunk indices and filenames from tool output like [1] (filename). "
                        "If no context is available, state that clearly."
                    ),
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("user", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        agent = _create_agent(self.llm, self.tools, prompt)
        self.executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=False,
            handle_parsing_errors=True,
            memory=self.memory,
        )

    def run(self, question: str) -> str:
        """Run the agent to answer a user question."""
        result = self.executor.invoke({"input": question})
        return result.get("output", "")

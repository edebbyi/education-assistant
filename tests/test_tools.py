from src.core.tools import build_tools


class DummyProcessor:
    def list_stored_documents(self):
        return [
            {"filename": "file-a.pdf", "uploaded_at": "2024-01-01"},
            {"filename": "file-b.pdf", "uploaded_at": "2024-01-02"},
        ]

    def get_context(self, question, specific_document=None, return_metadata=False):
        assert return_metadata is True
        return [
            {"text": "Alpha content", "filename": "file-a.pdf"},
            {"text": "Beta content", "filename": "file-b.pdf"},
        ]


def _get_tool(tools, name):
    return next(tool for tool in tools if tool.name == name)


def test_list_documents_formats_entries():
    tools = build_tools(DummyProcessor())
    list_tool = _get_tool(tools, "list_documents")

    output = list_tool.func()

    assert "file-a.pdf" in output
    assert "file-b.pdf" in output


def test_search_documents_formats_sources():
    tools = build_tools(DummyProcessor())
    search_tool = _get_tool(tools, "search_documents")

    output = search_tool.func("test query", None, 5)

    assert "[1]" in output
    assert "(file-a.pdf)" in output
    assert "(file-b.pdf)" in output


def test_summarize_text_fallback_without_llm():
    tools = build_tools(DummyProcessor(), summarizer_llm=None)
    summarize_tool = _get_tool(tools, "summarize_text")
    text = "Line one.\nLine two."

    output = summarize_tool.func(text)

    assert output.startswith("• ")
    assert len(output) <= 503  # ensures truncation logic never expands text


def test_summarize_last_answer_uses_getter():
    tools = build_tools(
        DummyProcessor(),
        summarizer_llm=None,
        get_last_answer=lambda: "Previous answer content",
    )
    summarize_last_tool = _get_tool(tools, "summarize_last_answer")

    output = summarize_last_tool.func()

    assert "Previous answer content" in output

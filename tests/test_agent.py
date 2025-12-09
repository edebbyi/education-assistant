from src.core.agent import AgentResponder


class DummyProcessor:
    def list_stored_documents(self):
        return []

    def get_context(self, question, specific_document=None, return_metadata=False):
        return []


class DummyExecutor:
    def __init__(self):
        self.calls = []

    def invoke(self, values):
        self.calls.append(values)
        return {"output": f"Echo: {values.get('input')}"}


def test_agent_responder_uses_injected_executor():
    processor = DummyProcessor()
    executor = DummyExecutor()

    agent = AgentResponder(
        processor=processor,
        executor=executor,
        llm=None,
        summarizer_llm=None,
        last_answer_getter=lambda: "prev answer",
    )

    result = agent.run("Hello agent")

    assert result == "Echo: Hello agent"
    assert executor.calls[0]["input"] == "Hello agent"

from finance_feedback_engine.decision_engine.local_llm_provider import LocalLLMProvider


class SequenceClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def generate(self, **kwargs):
        self.calls += 1
        return {"response": self.responses.pop(0)}

    def list(self):
        return {"models": [{"name": "mistral:latest"}]}


def test_query_retries_after_malformed_json_before_fallbacking_to_text_parse():
    provider = LocalLLMProvider.__new__(LocalLLMProvider)
    provider.config = {"decision_engine": {"max_retries": 2, "default_position_size": 0.1}}
    provider.model_name = "mistral:latest"
    provider.ollama_client = SequenceClient([
        '{',
        '{"action":"OPEN_SMALL_LONG","confidence":67,"reasoning":"retry recovered","amount":0.2}',
    ])
    provider.ensure_connection = lambda: None
    provider._unload_model = lambda: None

    decision = LocalLLMProvider.query(provider, "market prompt")

    assert provider.ollama_client.calls == 2
    assert decision["action"] == "OPEN_SMALL_LONG"
    assert decision["confidence"] == 67

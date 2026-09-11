import pytest

from backend.core.local_ai import LocalAIAdapter, LocalAIError
from backend.models.parser_proposal import ParserProposal


def test_local_ai_adapter_is_abstract():
    with pytest.raises(TypeError):
        LocalAIAdapter()


def test_local_ai_error_is_runtime_error():
    error = LocalAIError("local provider unavailable")

    assert isinstance(error, RuntimeError)
    assert str(error) == "local provider unavailable"


def test_local_ai_adapter_contract():
    class FakeLocalAI(LocalAIAdapter):
        def generate_parser_proposal(
            self,
            raw_log: str,
            evidence: dict,
        ) -> ParserProposal:
            return ParserProposal(
                parser_name="fake_device",
                format_type=evidence["format_type"],
                confidence=0.8,
                source="local_ai",
            )

    adapter = FakeLocalAI()

    proposal = adapter.generate_parser_proposal(
        raw_log="event=test user=admin",
        evidence={
            "format_type": "key_value",
        },
    )

    assert isinstance(proposal, ParserProposal)
    assert proposal.parser_name == "fake_device"
    assert proposal.format_type == "key_value"
    assert proposal.confidence == 0.8
    assert proposal.source == "local_ai"
from backend.core.local_ai_mock import DeterministicLocalAI
from backend.core.pipeline import LogProcessingPipeline


def test_pipeline_generates_valid_parser_proposal():
    pipeline = LogProcessingPipeline()
    adapter = DeterministicLocalAI()

    raw_log = (
        "2026-09-11T10:30:22Z "
        "DEVICE_X login "
        "user=admin src=10.0.0.5 result=failed"
    )

    proposal = pipeline.generate_parser_proposal(
        raw_log=raw_log,
        adapter=adapter,
    )

    assert proposal.parser_name == "unknown_device"
    assert proposal.format_type == "key_value"
    assert proposal.timestamp_field == "timestamp"
    assert proposal.mappings["user"] == "user"
    assert proposal.mappings["src"] == "source.ip"


def test_pipeline_proposal_generation_does_not_register_parser():
    pipeline = LogProcessingPipeline()
    adapter = DeterministicLocalAI()

    raw_log = "DEVICE_X user=admin src=10.0.0.5"

    proposal = pipeline.generate_parser_proposal(
        raw_log=raw_log,
        adapter=adapter,
    )

    assert proposal.parser_name == "unknown_device"

    try:
        pipeline.process(raw_log)
    except Exception as exc:
        assert "No registered parser detected" in str(exc)
    else:
        raise AssertionError(
            "Proposal generation must not register the parser"
        )
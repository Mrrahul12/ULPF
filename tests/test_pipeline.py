"""Tests for the Step 4 processing pipeline."""

import pytest

from backend.core.pipeline import LogProcessingPipeline, PipelineError, register_builtin_parsers
from backend.parsers.registry import reset_registry


@pytest.fixture
def pipeline():
    reset_registry()
    register_builtin_parsers()
    return LogProcessingPipeline()


def test_pipeline_returns_canonical_fortinet_event(pipeline):
    raw = 'date=2026-09-09 time=20:31:22 devname="FW01" srcip=10.0.0.5 dstip=192.168.1.20 srcport=443 dstport=8443 action=deny'

    event = pipeline.process(raw)

    assert event.source.ip == "10.0.0.5"
    assert event.destination.port == 8443
    assert event.event.action == "deny"
    assert event.observer.vendor == "Fortinet"
    assert event.raw.message == raw
    assert event.provenance.parser == "fortinet"
    assert event.unmapped["date"] == "2026-09-09"


def test_pipeline_preserves_json_unmapped_fields(pipeline):
    raw = '{"timestamp":"2026-09-09T20:31:22Z","src_ip":"10.0.0.5","custom":"keep-me"}'

    event = pipeline.process(raw)

    assert event.timestamp.isoformat().startswith("2026-09-09T20:31:22")
    assert event.unmapped["custom"] == "keep-me"
    assert event.raw.message == raw


def test_pipeline_rejects_unknown_logs(pipeline):
    with pytest.raises(PipelineError, match="No registered parser"):
        pipeline.process("not a recognized log")


def test_pipeline_rejects_invalid_ports(pipeline):
    raw = 'date=2026-09-09 devname="FW01" srcip=10.0.0.5 dstip=192.168.1.20 srcport=70000'

    with pytest.raises(PipelineError):
        pipeline.process(raw)

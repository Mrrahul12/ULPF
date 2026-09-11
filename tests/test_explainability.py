from backend.core.explainability import (
    explain_event,
    explain_field,
)
from backend.core.pipeline import (
    LogProcessingPipeline,
    register_builtin_parsers,
)


def setup_pipeline():
    register_builtin_parsers()
    return LogProcessingPipeline()


def test_explain_deterministic_field():
    pipeline = setup_pipeline()

    raw = (
        'date=2026-09-09 time=20:31:22 devname="FW01" '
        'srcip=10.0.0.5 dstip=192.168.1.20 '
        'srcport=443 dstport=8443 action=deny '
        'protocol="TCP/HTTPS" type=traffic'
    )

    event = pipeline.process(raw)

    explanation = explain_field(
        event.provenance,
        "source.ip",
    )

    assert explanation.field == "source.ip"
    assert explanation.value == "10.0.0.5"
    assert explanation.source_field == "srcip"
    assert explanation.parser == "fortinet"
    assert explanation.parser_version == "1.0"
    assert explanation.method == "deterministic"
    assert explanation.confidence == 1.0
    assert "srcip" in explanation.explanation
    assert "deterministically" in explanation.explanation
    assert "100%" in explanation.explanation

def test_explain_inferred_field():
    pipeline = setup_pipeline()

    raw = (
        "2026-09-09T20:31:22Z "
        "server01 app[1234]: "
        "Connection from 10.0.0.5 to 192.168.1.20"
    )

    event = pipeline.process(raw)

    assert event.provenance.parser == "syslog"

    fields = event.provenance.fields

    assert "source.ip" in fields

    explanation = explain_field(
        event.provenance,
        "source.ip",
    )

    assert explanation.method == "inferred"
    assert explanation.source_field == "message"
    assert explanation.value == "10.0.0.5"
    assert explanation.parser == "syslog"
    assert "inferred" in explanation.explanation


def test_explain_event():
    pipeline = setup_pipeline()

    raw = (
        'date=2026-09-09 time=20:31:22 devname="FW01" '
        'srcip=10.0.0.5 dstip=192.168.1.20 '
        'action=deny protocol="TCP/HTTPS" type=traffic'
    )

    event = pipeline.process(raw)

    explanations = explain_event(event.provenance)

    assert explanations
    assert all(item.field for item in explanations)
    assert any(
        item.field == "source.ip"
        for item in explanations
    )


def test_explain_unknown_field():
    pipeline = setup_pipeline()

    raw = (
        'date=2026-09-09 time=20:31:22 devname="FW01" '
        'srcip=10.0.0.5 dstip=192.168.1.20 '
        'action=deny protocol="TCP/HTTPS" type=traffic'
    )

    event = pipeline.process(raw)

    try:
        explain_field(
            event.provenance,
            "does.not.exist",
        )
        assert False, "Expected KeyError"
    except KeyError as exc:
        assert "does.not.exist" in str(exc)
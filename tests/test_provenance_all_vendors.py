from pathlib import Path
import json

from backend.core.pipeline import (
    LogProcessingPipeline,
    register_builtin_parsers,
)


ROOT = Path(__file__).resolve().parents[1]
DEMO_DATA = ROOT / "demo_data"


def setup_pipeline():
    register_builtin_parsers()
    return LogProcessingPipeline()


def test_cisco_provenance():
    pipeline = setup_pipeline()

    fixture = DEMO_DATA / "cisco_asa" / "security.log"
    raw = fixture.read_text(encoding="utf-8").splitlines()[0]

    event = pipeline.process(raw)

    assert event.provenance.parser == "cisco"

    fields = event.provenance.fields

    assert "event.severity" in fields
    assert fields["event.severity"].source_field == "severity"

    assert "source.ip" in fields
    assert fields["source.ip"].source_field == "source_ip"

    assert "source.port" in fields
    assert fields["source.port"].source_field == "source_port"


def test_fortinet_provenance():
    pipeline = setup_pipeline()

    fixture = DEMO_DATA / "fortinet" / "traffic.log"
    raw = fixture.read_text(encoding="utf-8").splitlines()[0]

    event = pipeline.process(raw)

    assert event.provenance.parser == "fortinet"

    fields = event.provenance.fields

    assert fields["source.ip"].source_field == "srcip"
    assert fields["destination.ip"].source_field == "dstip"
    assert fields["source.port"].source_field == "srcport"
    assert fields["destination.port"].source_field == "dstport"


def test_paloalto_provenance():
    pipeline = setup_pipeline()

    fixture = DEMO_DATA / "paloalto" / "traffic.log"
    raw = fixture.read_text(encoding="utf-8").splitlines()[0]

    event = pipeline.process(raw)

    assert event.provenance.parser == "paloalto"

    fields = event.provenance.fields

    assert fields["source.ip"].source_field == "srcip"
    assert fields["destination.ip"].source_field == "dstip"
    assert "source.port" not in fields
    assert "destination.port" not in fields


def test_json_provenance():
    pipeline = setup_pipeline()

    fixture = DEMO_DATA / "json" / "events.json"

    event_data = json.loads(
        fixture.read_text(encoding="utf-8")
    )[0]

    raw = json.dumps(event_data)

    event = pipeline.process(raw)

    assert event.provenance.parser == "json"

    fields = event.provenance.fields

    assert fields["source.ip"].source_field == "src_ip"
    assert fields["destination.ip"].source_field == "dst_ip"
    assert fields["event.action"].source_field == "action"


def test_syslog_provenance():
    pipeline = setup_pipeline()

    fixture = DEMO_DATA / "syslog" / "rfc5424.log"
    raw = fixture.read_text(encoding="utf-8").splitlines()[0]

    event = pipeline.process(raw)

    assert event.provenance.parser == "syslog"

    fields = event.provenance.fields

    assert fields["timestamp"].source_field == "timestamp"
    assert fields["observer.hostname"].source_field == "hostname"

    if "source.ip" in fields:
        assert fields["source.ip"].source_field == "message"
        assert fields["source.ip"].method == "inferred"
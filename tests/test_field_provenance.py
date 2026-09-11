from backend.core.pipeline import LogProcessingPipeline, register_builtin_parsers


def setup_pipeline():
    register_builtin_parsers()
    return LogProcessingPipeline()


def test_fortinet_field_level_provenance():
    pipeline = setup_pipeline()

    raw = (
        'date=2026-09-09 time=20:31:22 devname="FW01" '
        'srcip=10.0.0.5 dstip=192.168.1.20 '
        'srcport=443 dstport=8443 action=deny '
        'protocol="TCP/HTTPS" type=traffic'
    )

    event = pipeline.process(raw)

    assert event.source.ip == "10.0.0.5"
    assert event.destination.ip == "192.168.1.20"

    fields = event.provenance.fields

    assert "source.ip" in fields
    assert fields["source.ip"].source_field == "srcip"
    assert fields["source.ip"].value == "10.0.0.5"
    assert fields["source.ip"].method == "deterministic"

    assert "destination.ip" in fields
    assert fields["destination.ip"].source_field == "dstip"


def test_field_provenance_preserves_parser_metadata():
    pipeline = setup_pipeline()

    raw = (
        'date=2026-09-09 time=20:31:22 devname="FW01" '
        'srcip=10.0.0.5 dstip=192.168.1.20 '
        'action=deny protocol="TCP/HTTPS" type=traffic'
    )

    event = pipeline.process(raw)

    assert event.provenance.parser == "fortinet"
    assert event.provenance.parser_version == "1.0"
    assert event.provenance.mapping_version == "1.0"
    assert event.provenance.confidence == 1.0


def test_field_provenance_does_not_remove_unmapped_fields():
    pipeline = setup_pipeline()

    raw = (
        'date=2026-09-09 time=20:31:22 devname="FW01" '
        'srcip=10.0.0.5 dstip=192.168.1.20 '
        'sessionid=98231 policy_id=17 '
        'action=deny protocol="TCP/HTTPS" type=traffic'
    )

    event = pipeline.process(raw)

    assert "sessionid" in event.unmapped
    assert "policy_id" in event.unmapped
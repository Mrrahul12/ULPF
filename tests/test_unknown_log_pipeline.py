from backend.core.pipeline import LogProcessingPipeline


def test_pipeline_can_analyze_unknown_log():
    pipeline = LogProcessingPipeline()

    raw = (
        "2026-09-11T10:30:22Z "
        "DEVICE_X EVENT login "
        "user=admin src=10.0.0.5 result=failed"
    )

    analysis = pipeline.analyze_unknown(raw)

    assert analysis.is_unknown is True
    assert analysis.format_type == "key_value"
    assert analysis.timestamp_detected is True
    assert "user" in analysis.key_value_fields
    assert "src" in analysis.key_value_fields
    assert "10.0.0.5" in analysis.ip_addresses


def test_pipeline_unknown_analysis_does_not_change_process_contract(monkeypatch):
    pipeline = LogProcessingPipeline()

    raw = "DEVICE_X authentication failure for admin"

    analysis = pipeline.analyze_unknown(raw)

    assert analysis.is_unknown is True
    assert analysis.format_type == "plain_text"

    # Force the pipeline's detector to report an unknown source.
    monkeypatch.setattr(
        pipeline.detector,
        "detect",
        lambda _: "unknown",
    )

    try:
        pipeline.process(raw)
    except Exception as exc:
        assert "No registered parser detected" in str(exc)
    else:
        raise AssertionError("Unknown log should still be rejected by process()")
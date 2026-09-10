"""Contract tests for rolling-update resilience testing."""

from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_rolling_update_test_has_rollout_and_failure_guards():
    script = (ROOT / "k8s" / "rolling_update_test.py").read_text(encoding="utf-8")

    assert "rollout restart" in script
    assert "rollout status" in script
    assert "rollout_succeeded" in script
    assert "http_error_statuses" in script
    assert "trace_ids_observed" in script

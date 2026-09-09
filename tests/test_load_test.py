"""Contract tests for the Kubernetes load-test utility."""

from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_load_test_exposes_concurrency_and_summary_options():
    script = (ROOT / "k8s" / "load_test.py").read_text(encoding="utf-8")

    assert "ThreadPoolExecutor" in script
    assert "--requests" in script
    assert "--workers" in script
    assert "average_latency_ms" in script
    assert "trace_ids_observed" in script

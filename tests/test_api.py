"""Tests for the ULPF FastAPI service."""

from fastapi.testclient import TestClient

from backend.api import main
from backend.api.main import app
from backend.api.security import RateLimiter


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]
    assert len(response.headers["X-Trace-ID"]) == 32


def test_request_id_is_preserved():
    response = client.get("/health", headers={"X-Request-ID": "test-request-id"})

    assert response.headers["X-Request-ID"] == "test-request-id"
    assert len(response.headers["X-Trace-ID"]) == 32


def test_parse_endpoint_returns_canonical_event():
    raw = 'date=2026-09-09 devname="FW01" srcip=10.0.0.5 dstip=192.168.1.20 action=deny'

    response = client.post("/parse", json={"message": raw})
    body = response.json()

    assert response.status_code == 200
    assert body["accepted"] is True
    assert body["event"]["raw"]["message"] == raw
    assert body["event"]["source"]["ip"] == "10.0.0.5"
    assert body["event"]["event"]["action"] == "deny"
    assert body["event"]["provenance"]["parser"] == "fortinet"


def test_parse_endpoint_returns_structured_error():
    response = client.post("/parse", json={"message": "unrecognized text"})
    body = response.json()

    assert response.status_code == 200
    assert body["accepted"] is False
    assert body["event"] is None
    assert body["error"]["status"] == "parse_failure"
    assert body["error"]["raw_message"] == "unrecognized text"


def test_parse_endpoint_rejects_missing_message():
    response = client.post("/parse", json={})

    assert response.status_code == 422

def test_parse_endpoint_rejects_empty_message():
    response = client.post("/parse", json={"message": ""})

    assert response.status_code == 422


def test_parse_endpoint_rejects_whitespace_message():
    response = client.post("/parse", json={"message": "   \n\t   "})

    assert response.status_code == 422


def test_parse_endpoint_rejects_oversized_message():
    oversized = "A" * (main.MAX_LOG_MESSAGE_LENGTH + 1)

    response = client.post(
        "/parse",
        json={"message": oversized},
    )

    assert response.status_code == 422


def test_parse_endpoint_accepts_maximum_message_size():
    message = "A" * main.MAX_LOG_MESSAGE_LENGTH

    response = client.post(
        "/parse",
        json={"message": message},
    )

    assert response.status_code == 200

def test_parse_endpoint_requires_configured_api_key(monkeypatch):
    monkeypatch.setenv("ULPF_API_KEY", "test-secret")
    raw = 'date=2026-09-09 devname="FW01" srcip=10.0.0.5 dstip=192.168.1.20'

    unauthorized = client.post("/parse", json={"message": raw})
    authorized = client.post(
        "/parse",
        json={"message": raw},
        headers={"X-API-Key": "test-secret"},
    )

    assert unauthorized.status_code == 401
    assert authorized.status_code == 200
    assert authorized.json()["accepted"] is True

def test_parse_endpoint_rejects_wrong_api_key(monkeypatch):
    monkeypatch.setenv("ULPF_API_KEY", "correct-secret")
    raw = 'date=2026-09-09 devname="FW01" srcip=10.0.0.5'

    response = client.post(
        "/parse",
        json={"message": raw},
        headers={"X-API-Key": "wrong-secret"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_parse_endpoint_does_not_leak_configured_api_key(monkeypatch):
    secret = "super-secret-api-key"
    monkeypatch.setenv("ULPF_API_KEY", secret)

    response = client.post(
        "/parse",
        json={"message": "test"},
        headers={"X-API-Key": "wrong-key"},
    )

    assert response.status_code == 401
    assert secret not in response.text

def test_parse_endpoint_enforces_rate_limit(monkeypatch):
    original_limiter = main.rate_limiter
    main.rate_limiter = RateLimiter(limit=1, window_seconds=60)
    monkeypatch.delenv("ULPF_API_KEY", raising=False)
    raw = 'date=2026-09-09 devname="FW01" srcip=10.0.0.5 dstip=192.168.1.20'

    first = client.post("/parse", json={"message": raw})
    second = client.post("/parse", json={"message": raw})

    main.rate_limiter = original_limiter
    assert first.status_code == 200
    assert second.status_code == 429


def test_metrics_endpoint_returns_counters():
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "total_requests" in response.json()
    assert "successful_parses" in response.json()


def test_prometheus_metrics_endpoint_returns_counters():
    response = client.get("/metrics/prometheus")

    assert response.status_code == 200
    assert "ulpf_requests_total" in response.text
    assert "# TYPE ulpf_parse_success_total counter" in response.text

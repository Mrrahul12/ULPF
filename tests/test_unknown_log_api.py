from fastapi.testclient import TestClient

from backend.api.main import app


client = TestClient(app)


def test_unknown_log_analysis_api():
    response = client.post(
        "/api/unknown/analyze",
        json={
            "raw_log": (
                "2026-09-11T10:30:22Z "
                "DEVICE_X EVENT login "
                "user=admin src=10.0.0.5 result=failed"
            )
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["is_unknown"] is True
    assert data["format_type"] == "key_value"
    assert data["timestamp_detected"] is True
    assert "user" in data["key_value_fields"]
    assert "src" in data["key_value_fields"]
    assert "10.0.0.5" in data["ip_addresses"]


def test_unknown_log_analysis_api_rejects_invalid_input():
    response = client.post(
        "/api/unknown/analyze",
        json={"raw_log": 12345},
    )

    assert response.status_code == 400
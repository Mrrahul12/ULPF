from fastapi.testclient import TestClient

from backend.api.main import app


client = TestClient(app)


def test_parser_factory_api_generates_proposal():
    response = client.post(
        "/api/parser-factory/propose",
        json={
            "raw_log": (
                "2026-09-11T10:30:22Z "
                "DEVICE_X login "
                "user=admin src=10.0.0.5 result=failed"
            )
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["parser_name"] == "unknown_device"
    assert data["format_type"] == "key_value"
    assert data["timestamp_field"] == "timestamp"
    assert data["mappings"]["user"] == "user"
    assert data["mappings"]["src"] == "source.ip"
    assert data["source"] == "local_ai"


def test_parser_factory_api_rejects_empty_log():
    response = client.post(
        "/api/parser-factory/propose",
        json={
            "raw_log": "",
        },
    )

    assert response.status_code == 400


def test_parser_factory_api_rejects_non_string_log():
    response = client.post(
        "/api/parser-factory/propose",
        json={
            "raw_log": 12345,
        },
    )

    assert response.status_code == 400
from backend.core.dynamic_registry import reset_dynamic_registry
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from backend.api.main import app


client = TestClient(app)


def approved_payload():
    return {
        "definition": {
            "parser_name": "api_dynamic_parser",
            "format_type": "key_value",
            "mappings": {
                "action": "event_type",
                "src_ip": "source_ip",
            },
            "timestamp_field": "timestamp",
        },
        "approval": {
            "parser_name": "api_dynamic_parser",
            "status": "approved",
            "reviewer": "security_admin",
            "comment": "Approved",
            "created_at": "2026-09-11T10:00:00Z",
            "reviewed_at": "2026-09-11T10:05:00Z",
        },
        "vendor": "ExampleVendor",
        "product": "ExampleFirewall",
        "confidence": 0.95,
        "source": "local_ai",
    }


def test_register_dynamic_parser_api():
    response = client.post(
        "/api/dynamic-parsers/register",
        json=approved_payload(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["parser_name"] == "api_dynamic_parser"
    assert data["vendor"] == "ExampleVendor"
    assert data["confidence"] == 0.95
    assert data["approved_by"] == "security_admin"


def test_register_pending_parser_api():
    payload = approved_payload()

    payload["definition"]["parser_name"] = "pending_api_parser"
    payload["approval"]["parser_name"] = "pending_api_parser"
    payload["approval"]["status"] = "pending"

    response = client.post(
        "/api/dynamic-parsers/register",
        json=payload,
    )

    assert response.status_code == 400


def test_register_rejected_parser_api():
    payload = approved_payload()

    payload["definition"]["parser_name"] = "rejected_api_parser"
    payload["approval"]["parser_name"] = "rejected_api_parser"
    payload["approval"]["status"] = "rejected"

    response = client.post(
        "/api/dynamic-parsers/register",
        json=payload,
    )

    assert response.status_code == 400


def test_get_missing_dynamic_parser_api():
    response = client.get(
        "/api/dynamic-parsers/does_not_exist"
    )

    assert response.status_code == 404


def test_deactivate_missing_dynamic_parser_api():
    response = client.delete(
        "/api/dynamic-parsers/does_not_exist"
    )

    assert response.status_code == 404


def setup_function():
    reset_dynamic_registry()


def test_registered_parser_persists_across_api_requests():
    payload = approved_payload()

    response = client.post(
        "/api/dynamic-parsers/register",
        json=payload,
    )

    assert response.status_code == 200

    response = client.get(
        "/api/dynamic-parsers/api_dynamic_parser"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["parser_name"] == "api_dynamic_parser"
    assert data["active"] is True    

def test_deactivate_registered_dynamic_parser_api():
    payload = approved_payload()

    response = client.post(
        "/api/dynamic-parsers/register",
        json=payload,
    )

    assert response.status_code == 200

    response = client.delete(
        "/api/dynamic-parsers/api_dynamic_parser"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["parser_name"] == "api_dynamic_parser"
    assert data["active"] is False


def test_deactivated_parser_metadata_remains_available():
    payload = approved_payload()

    response = client.post(
        "/api/dynamic-parsers/register",
        json=payload,
    )

    assert response.status_code == 200

    response = client.delete(
        "/api/dynamic-parsers/api_dynamic_parser"
    )

    assert response.status_code == 200

    response = client.get(
        "/api/dynamic-parsers/api_dynamic_parser"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["parser_name"] == "api_dynamic_parser"
    assert data["active"] is False


def test_deactivate_dynamic_parser_twice_api():
    payload = approved_payload()

    response = client.post(
        "/api/dynamic-parsers/register",
        json=payload,
    )

    assert response.status_code == 200

    response = client.delete(
        "/api/dynamic-parsers/api_dynamic_parser"
    )

    assert response.status_code == 200

    response = client.delete(
        "/api/dynamic-parsers/api_dynamic_parser"
    )

    assert response.status_code == 400
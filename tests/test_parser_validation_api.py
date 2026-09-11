from fastapi.testclient import TestClient

from backend.api.main import app


client = TestClient(app)


def test_parser_validation_api_passes_valid_parser():
    response = client.post(
        "/api/parser-factory/validate",
        json={
            "definition": {
                "parser_name": "device_parser",
                "format_type": "key_value",
                "mappings": {
                    "src_ip": "source_ip",
                },
            },
            "raw_log": "src_ip=10.0.0.1",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["passed"] is True
    assert data["total_tests"] == 1
    assert data["passed_tests"] == 1
    assert data["failed_tests"] == 0


def test_parser_validation_api_rejects_unsafe_parser():
    response = client.post(
        "/api/parser-factory/validate",
        json={
            "definition": {
                "parser_name": "device_parser",
                "format_type": "plain_text",
                "mappings": {
                    "__import__('os').system('whoami')": "message",
                },
            },
            "raw_log": "normal log",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["passed"] is False
    assert data["failed_tests"] == 1


def test_parser_validation_api_returns_results():
    response = client.post(
        "/api/parser-factory/validate",
        json={
            "definition": {
                "parser_name": "device_parser",
                "format_type": "key_value",
                "mappings": {
                    "src_ip": "source_ip",
                },
            },
            "raw_log": "src_ip=192.168.1.10",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["results"]) == 1
    assert data["results"][0]["name"] == "basic_parser_test"
    assert data["results"][0]["passed"] is True
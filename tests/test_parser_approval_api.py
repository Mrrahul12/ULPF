from fastapi.testclient import TestClient

from backend.api.main import app


client = TestClient(app)


def test_approve_parser_api():
    response = client.post(
        "/api/parser-approval/approve",
        json={
            "parser_name": "device_parser",
            "reviewer": "security_admin",
            "comment": "Approved after validation.",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["parser_name"] == "device_parser"
    assert data["status"] == "approved"
    assert data["reviewer"] == "security_admin"
    assert data["comment"] == "Approved after validation."
    assert data["reviewed_at"] is not None


def test_reject_parser_api():
    response = client.post(
        "/api/parser-approval/reject",
        json={
            "parser_name": "device_parser",
            "reviewer": "security_admin",
            "comment": "Field mapping is incorrect.",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["parser_name"] == "device_parser"
    assert data["status"] == "rejected"
    assert data["reviewer"] == "security_admin"
    assert data["comment"] == "Field mapping is incorrect."
    assert data["reviewed_at"] is not None


def test_approve_parser_requires_reviewer():
    response = client.post(
        "/api/parser-approval/approve",
        json={
            "parser_name": "device_parser",
            "reviewer": "",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "reviewer is required"
"""
Tests for system health check, documentation, and CORS endpoints.
"""


def test_health_check_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "project_configured" in data
    assert "model" in data


def test_openapi_json_available(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert spec["openapi"].startswith("3.")
    assert "/generate" in spec["paths"]
    assert "/health" in spec["paths"]


def test_swagger_docs_available(client):
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower()

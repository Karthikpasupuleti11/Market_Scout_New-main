from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200


def test_swagger_docs():
    response = client.get("/docs")

    assert response.status_code == 200


def test_metrics_endpoint():
    response = client.get("/metrics")

    assert response.status_code == 200
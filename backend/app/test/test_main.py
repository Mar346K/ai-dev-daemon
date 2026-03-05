from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check() -> None:
    """
    Test the /health endpoint to ensure it returns a 200 OK and the correct JSON payload.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "ai_dev_daemon"}
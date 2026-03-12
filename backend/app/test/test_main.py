import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

def test_health_check() -> None:
    """
    Test the /health endpoint to ensure it returns a 200 OK and the correct JSON payload.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "ai_dev_daemon"}

def test_global_error_masking(monkeypatch):
    """Verify that internal exceptions are masked and do not leak sensitive data."""
    # We will intentionally monkeypatch the security function to simulate a fatal crash
    from app.core import security
    
    # ... (inside test_global_error_masking)
    def mock_crash(*args, **kwargs):
        raise RuntimeError("CRITICAL LEAK: Database password is 'hunter2'")
        
    # FIX: Patch the reference inside app.main, not the original module
    monkeypatch.setattr("app.main.secure_resolve_path", mock_crash)
    
    # Send a request that will trigger the crash
    response = client.post("/compile-context", json={"project_path": "/fake/path"})
    # ...

    assert response.status_code == 500
    data = response.json()
    
    # The client must receive a masked error, NOT the raw exception
    assert "detail" in data
    assert "Internal server error" in data["detail"]
    assert "hunter2" not in data["detail"]
    assert "CRITICAL LEAK" not in data["detail"]
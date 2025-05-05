from fastapi.testclient import TestClient

# Adjust the import path based on your project structure
# If tests are run from the root, this should work.
# If run from backend/, it might need adjustment (e.g., from main import app)
from backend.main import app 

client = TestClient(app)

def test_health_check():
    response = client.get("/api/v1/health/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"} 
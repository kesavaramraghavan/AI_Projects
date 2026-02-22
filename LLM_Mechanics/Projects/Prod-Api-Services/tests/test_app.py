from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_estimate_basic():
    resp = client.post(
        "/estimate",
        json={"prompt": "Hello world", "max_completion_tokens": 256},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["prompt_tokens"] > 0
    assert isinstance(data["estimated_max_cost_usd"], float)

def test_health():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
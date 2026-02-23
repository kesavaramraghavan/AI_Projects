from fastapi.testclient import TestClient
from unittest.mock import patch
from api.app import app

client = TestClient(app)

MOCK_RESPONSE = {
    "choices": [
        {
            "message": {"content": "API test response"},
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "total_tokens": 20
    }
}


@patch("gen_controls.client.OpenRouterClient.generate")
def test_generate_endpoint(mock_generate):
    mock_generate.return_value = MOCK_RESPONSE

    payload = {
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 100,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "stop": []
    }

    response = client.post(
        "/generate?prompt=Hello",
        json=payload
    )

    assert response.status_code == 200
    data = response.json()

    assert data["text"] == "API test response"
    assert data["finish_reason"] == "stop"
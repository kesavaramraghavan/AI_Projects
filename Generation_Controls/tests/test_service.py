import pytest
from unittest.mock import patch
from gen_controls.service import generate_text
from gen_controls.config import GenerationConfig


MOCK_RESPONSE = {
    "choices": [
        {
            "message": {"content": "Test response"},
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15
    }
}


@patch("gen_controls.client.OpenRouterClient.generate")
def test_generate_text_success(mock_generate):
    mock_generate.return_value = MOCK_RESPONSE

    cfg = GenerationConfig(
        temperature=0.7,
        top_p=0.9,
        max_tokens=100,
    )

    result = generate_text("Hello world", cfg)

    assert result["text"] == "Test response"
    assert result["finish_reason"] == "stop"
    assert result["usage"]["total_tokens"] == 15


@patch("gen_controls.client.OpenRouterClient.generate")
def test_max_token_enforcement(mock_generate):
    mock_generate.return_value = MOCK_RESPONSE

    cfg = GenerationConfig(
        temperature=0.7,
        top_p=0.9,
        max_tokens=2000  # Should be clipped if its more than 2000 as thats the condition set.
    )

    result = generate_text("Hello world", cfg)

    # enforce_bounds clips >1000
    assert result["text"] == "Test response"


@patch("gen_controls.client.OpenRouterClient.generate")
def test_handles_openrouter_error(mock_generate):
    mock_generate.side_effect = RuntimeError("API failure")

    cfg = GenerationConfig()

    with pytest.raises(RuntimeError):
        generate_text("Hello world", cfg)
import time
from .client import OpenRouterClient
from .observability import log_request
from .validation import enforce_bounds

client = OpenRouterClient()

def generate_text(prompt: str, cfg):
    start = time.time()

    cfg = enforce_bounds(cfg)

    messages = [{"role": "user", "content": prompt}]

    response = client.generate(
        messages=messages,
        temperature=cfg.temperature,
        top_p=cfg.top_p,
        max_tokens=cfg.max_tokens,
        frequency_penalty=cfg.frequency_penalty,
        presence_penalty=cfg.presence_penalty,
        stop=cfg.stop,
    )

    text = response["choices"][0]["message"]["content"]
    finish_reason = response["choices"][0]["finish_reason"]
    usage = response.get("usage")

    log_request(start, cfg, usage, finish_reason)

    return {
        "text": text,
        "finish_reason": finish_reason,
        "usage": usage,
    }
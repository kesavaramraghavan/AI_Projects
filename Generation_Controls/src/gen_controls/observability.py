import time

def log_request(start_time, cfg, usage, stop_reason):
    latency = round((time.time() - start_time) * 1000, 2)
    print({
        "latency_ms": latency,
        "temperature": cfg.temperature,
        "top_p": cfg.top_p,
        "max_tokens": cfg.max_tokens,
        "freq_penalty": cfg.frequency_penalty,
        "pres_penalty": cfg.presence_penalty,
        "stop_reason": stop_reason,
        "total_tokens": usage.get("total_tokens") if usage else None
    })
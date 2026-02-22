# File: api/app/main.py

from fastapi import FastAPI, Request
from fastapi.responses import Response, FileResponse, JSONResponse
from prometheus_client import generate_latest, Counter, Histogram
import logging
import os
from .services import process_estimate
from .middleware import APIKeyMiddleware, RequestContextMiddleware
from .logging_config import setup_logging
from fastapi.staticfiles import StaticFiles

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Token Estimator Service", version="2.0.0")

# Middleware
app.add_middleware(RequestContextMiddleware)
app.add_middleware(APIKeyMiddleware, exempt_paths=["/static", "/metrics"])

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Prometheus metrics
REQUEST_COUNT = Counter("request_count", "Total requests")
REQUEST_LATENCY = Histogram("request_latency_seconds", "Request latency in seconds")

# In-memory conversation memory per user
USER_MEMORY = {}

@app.get("/healthz")
def health():
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")

@app.get("/static/index.html")
def get_html():
    return FileResponse(os.path.join(os.path.dirname(__file__), "../static/index.html"))

@app.post("/estimate")
def estimate(req: dict, request: Request):
    user_id = request.headers.get("x-user-id", "anonymous")
    prompt = req.get("prompt", "")
    max_completion = req.get("max_completion_tokens", 256)

    # Append previous conversation memory
    memory_prompt = ""
    if user_id in USER_MEMORY:
        memory_prompt = "\n".join(USER_MEMORY[user_id]) + "\n"

    full_prompt = memory_prompt + prompt

    import time
    start = time.perf_counter()
    result = process_estimate(full_prompt, max_completion, user_id)
    duration = time.perf_counter() - start

    REQUEST_COUNT.inc()
    REQUEST_LATENCY.observe(duration)

    # Save new conversation in memory
    if user_id not in USER_MEMORY:
        USER_MEMORY[user_id] = []
    USER_MEMORY[user_id].append(f"User: {prompt}")
    USER_MEMORY[user_id].append(f"Bot: {result['model_response']}")

    logger.info({
        "user_id": user_id,
        "prompt": prompt,
        "prompt_tokens": result["prompt_tokens"],
        "completion_tokens": result["completion_tokens"],
        "fits_context": result["fits_context"],
        "estimated_max_cost_usd": result["estimated_max_cost_usd"],
        "model_response": result["model_response"],
        "duration_ms": round(duration * 1000, 2),
    })

    return {"response": result["model_response"].replace("\n", " ")}


@app.post("/clear")
def clear_memory(request: Request):
    user_id = request.headers.get("x-user-id", "anonymous")
    USER_MEMORY[user_id] = []
    return JSONResponse({"status": "memory_cleared"})
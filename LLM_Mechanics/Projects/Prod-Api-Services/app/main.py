from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response, JSONResponse
from prometheus_client import generate_latest
import logging
import time

from .models import EstimateRequest
from .services import process_estimate
from .logging_config import setup_logging
from .middleware import RequestContextMiddleware, APIKeyMiddleware
from .metrics import REQUEST_COUNT, REQUEST_LATENCY

# Setup structured logging
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Token Estimator Service",
    version="2.0.0",
    description="Production-grade token estimator with auth, metrics, caching"
)

# Register middleware (order matters)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(APIKeyMiddleware)


@app.get("/healthz")
def health():
    """Liveness check"""
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type="text/plain")


@app.post("/estimate")
def estimate(req: EstimateRequest, request: Request):
    """
    Main estimation endpoint with safe error handling.
    """

    user_id = request.headers.get("x-user-id", "anonymous")

    start = time.perf_counter()
    try:
        # Wrap call in try-except to catch internal errors
        result = process_estimate(
            prompt=req.prompt,
            max_completion_tokens=req.max_completion_tokens,
            user_id=user_id,
        )
    except Exception as e:
        logger.error(f"Estimate processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    duration = time.perf_counter() - start

    # Update Prometheus metrics (safe)
    try:
        REQUEST_COUNT.inc()
        REQUEST_LATENCY.observe(duration)
    except Exception as e:
        logger.warning(f"Metrics update failed: {e}")

    # Log the request info
    logger.info(
        "estimate_request",
        extra={
            "user_id": user_id,
            "prompt_tokens": result.get("prompt_tokens", 0),
            "fits_context": result.get("fits_context", False),
            "estimated_cost": result.get("estimated_max_cost_usd", 0),
            "duration_ms": round(duration * 1000, 2),
        },
    )

    return JSONResponse(
        content={
            "prompt_tokens": result.get("prompt_tokens", 0),
            "fits_context": result.get("fits_context", False),
            "estimated_max_cost_usd": result.get("estimated_max_cost_usd", 0),
            "duration_ms": round(duration * 1000, 2),
        }
    )
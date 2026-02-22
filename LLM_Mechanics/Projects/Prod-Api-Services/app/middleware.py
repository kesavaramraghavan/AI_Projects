import uuid
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from .metrics import REQUEST_COUNT, REQUEST_LATENCY
from fastapi.responses import JSONResponse
from .config import API_KEY

class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path not in ["/healthz", "/metrics"]:
            key = request.headers.get("x-api-key")
            if key != API_KEY:
                return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
        return await call_next(request)

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        response = await call_next(request)

        duration = time.perf_counter() - start

        REQUEST_COUNT.inc()
        REQUEST_LATENCY.observe(duration)

        response.headers["X-Request-ID"] = request_id
        return response
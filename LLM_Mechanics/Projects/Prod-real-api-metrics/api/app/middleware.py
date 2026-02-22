# Filename: middleware.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # per-request context (optional)
        response = await call_next(request)
        return response

class APIKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, exempt_paths=None):
        super().__init__(app)
        self.exempt_paths = exempt_paths or []

    async def dispatch(self, request: Request, call_next):
        # Skip API key check for exempt paths
        for path in self.exempt_paths:
            if request.url.path.startswith(path):
                return await call_next(request)

        api_key = request.headers.get("x-api-key")
        if not api_key or api_key != "dev-secret-key":
            return JSONResponse({"detail": "Invalid API key"}, status_code=401)

        return await call_next(request)
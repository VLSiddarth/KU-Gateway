"""Middleware stubs."""
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, calls_per_minute=100):
        super().__init__(app)
        self.calls = calls_per_minute
    async def dispatch(self, request: Request, call_next):
        # simplified: no actual enforcement yet
        response = await call_next(request)
        return response

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        return response
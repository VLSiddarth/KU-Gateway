"""KU-Gateway: The Context Firewall for LLMs."""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from .config import Settings
from .proxy import router as proxy_router
from .telemetry import setup_logging
from .middleware import RateLimitMiddleware, AuthMiddleware
from .version import __version__

app = FastAPI(
    title="KU-Gateway",
    description="Context Firewall for LLMs",
    version=__version__,
)

# Setup logging
setup_logging()

# Load settings
settings = Settings()

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.add_middleware(RateLimitMiddleware, calls_per_minute=settings.rate_limit)
app.add_middleware(AuthMiddleware)

# Include routers
app.include_router(proxy_router)

@app.get("/")
async def root():
    return {
        "service": "KU-Gateway",
        "version": __version__,
        "status": "running",
        "docs": "/docs",
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": __version__,
        "ku_api_status": "connected",
        "cache_status": "connected" if settings.redis_enabled else "disabled",
    }

if __name__ == "__main__":
    uvicorn.run(
        "ku_gateway.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=settings.workers,
    )
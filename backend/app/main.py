from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.api.routes import health, invoices, vendors, pricing, upload

settings = get_settings()
setup_logging(level="DEBUG" if settings.app_debug else "INFO")

app = FastAPI(
    title="Maillard Back Office",
    description="Internal invoice processing system for Maillard.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router, tags=["health"])
app.include_router(upload.router, prefix=settings.api_prefix)
app.include_router(invoices.router, prefix=settings.api_prefix, tags=["invoices"])
app.include_router(vendors.router, prefix=settings.api_prefix, tags=["vendors"])
app.include_router(pricing.router, prefix=settings.api_prefix, tags=["pricing"])

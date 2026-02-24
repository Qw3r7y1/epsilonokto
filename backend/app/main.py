from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.api.routes import health, upload, invoices, vendors, pricing

settings = get_settings()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging("DEBUG" if settings.app_debug else "INFO")
    logger.info(f"Starting Maillard Back Office ({settings.app_env})")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Maillard Back Office",
    description="Internal invoice processing: upload → extract → store → compare",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS (for Retool / frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router)
app.include_router(upload.router, prefix=settings.api_prefix)
app.include_router(invoices.router, prefix=settings.api_prefix)
app.include_router(vendors.router, prefix=settings.api_prefix)
app.include_router(pricing.router, prefix=settings.api_prefix)

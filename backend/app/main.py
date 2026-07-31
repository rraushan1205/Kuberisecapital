from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.client_auth import router as client_auth_router
from app.api.client_brokers import router as client_brokers_router
from app.api.client import router as client_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import SessionLocal
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.services.admin_bootstrap import ensure_initial_super_admin
from app.services.brokers.implementations.fyers import FyersBroker
from app.services.brokers.registry import get_global_registry

# Configure logging
settings = get_settings()
configure_logging(settings.environment)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Bootstrap initial super admin
    logger.info("application_startup", message="Bootstrapping super admin")
    with SessionLocal() as session:
        ensure_initial_super_admin(session)

    # Register broker providers
    registry = get_global_registry()
    registry.register(FyersBroker)

    logger.info("application_ready", message="Application startup complete")
    yield
    logger.info("application_shutdown", message="Application shutting down")


settings = get_settings()
app = FastAPI(title="Stratum API", version="1.0.0", lifespan=lifespan)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)
app.include_router(admin_router)
app.include_router(auth_router)
app.include_router(client_auth_router)
app.include_router(client_brokers_router)
app.include_router(client_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}

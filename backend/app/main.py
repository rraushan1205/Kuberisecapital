from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.admin_strategies import router as admin_strategies_router
from app.api.auth import router as auth_router
from app.api.client_auth import router as client_auth_router
from app.api.client_auth_oauth import router as client_auth_oauth_router
from app.api.client_brokers import router as client_brokers_router
from app.api.client_strategies import router as client_strategies_router
from app.api.client_strategy_permissions import router as client_strategy_permissions_router
from app.api.client import router as client_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import SessionLocal
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.services.admin_bootstrap import ensure_initial_super_admin
from app.services.brokers.implementations.aliceblue import AliceBlueBroker
from app.services.brokers.implementations.fyers import FyersBroker
from app.services.brokers.manager import BrokerManager
from app.services.brokers.registry import get_global_registry
from app.services.strategy_scheduler import StrategyScheduler
from app.db.session import async_session_maker

# Configure logging
settings = get_settings()
configure_logging(settings.environment)
logger = get_logger(__name__)

# Global strategy scheduler instance
_strategy_scheduler: StrategyScheduler | None = None


def get_strategy_scheduler() -> StrategyScheduler:
    """Dependency to access the strategy scheduler"""
    if _strategy_scheduler is None:
        raise RuntimeError("StrategyScheduler not initialized")
    return _strategy_scheduler


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _strategy_scheduler
    
    # Bootstrap initial super admin
    logger.info("application_startup", message="Bootstrapping super admin")
    with SessionLocal() as session:
        ensure_initial_super_admin(session)

    # Register broker providers
    registry = get_global_registry()
    registry.register(FyersBroker)
    registry.register(AliceBlueBroker)
    
    # Initialize broker manager
    broker_manager = BrokerManager(registry)
    
    # Initialize and start strategy scheduler
    logger.info("application_startup", message="Initializing strategy scheduler")
    _strategy_scheduler = StrategyScheduler(
        db_session_maker=async_session_maker,
        broker_manager=broker_manager
    )
    await _strategy_scheduler.start()

    logger.info("application_ready", message="Application startup complete")
    yield
    
    # Shutdown strategy scheduler
    logger.info("application_shutdown", message="Stopping strategy scheduler")
    if _strategy_scheduler:
        await _strategy_scheduler.stop()
    
    logger.info("application_shutdown", message="Application shutting down")


settings = get_settings()
app = FastAPI(title="Kuberise Capital API", version="1.0.0", lifespan=lifespan)

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
app.include_router(admin_strategies_router)
app.include_router(auth_router)
app.include_router(client_auth_router)
app.include_router(client_auth_oauth_router)
app.include_router(client_brokers_router)
app.include_router(client_strategies_router)
app.include_router(client_strategy_permissions_router)
app.include_router(client_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}

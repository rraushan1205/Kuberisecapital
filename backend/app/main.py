from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.client_auth import router as client_auth_router
from app.api.client_brokers import router as client_brokers_router
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.admin_bootstrap import ensure_initial_super_admin
from app.services.brokers.implementations.fyers import FyersBroker
from app.services.brokers.registry import get_global_registry


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Bootstrap initial super admin
    with SessionLocal() as session:
        ensure_initial_super_admin(session)
    
    # Register broker providers
    registry = get_global_registry()
    registry.register(FyersBroker)
    
    yield


settings = get_settings()
app = FastAPI(title="Stratum API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(admin_router)
app.include_router(client_auth_router)
app.include_router(client_brokers_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}

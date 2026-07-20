from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.admin_bootstrap import ensure_initial_super_admin


@asynccontextmanager
async def lifespan(_: FastAPI):
    with SessionLocal() as session:
        ensure_initial_super_admin(session)
    yield


settings = get_settings()
app = FastAPI(title="Stratum API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(admin_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}

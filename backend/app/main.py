from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import check_connection
from app.api.v1.events import router as events_router
from app.api.v1.incidents import router as incidents_router
from app.api.v1.investigations import router as investigations_router

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events_router, prefix="/api/v1")
app.include_router(incidents_router, prefix="/api/v1")
app.include_router(investigations_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"service": settings.app_name, "env": settings.app_env}


@app.get("/health")
def health():
    """
    Reports whether the API is up AND whether it can reach Postgres.
    A health check that only confirms "the server responds" hides the
    most common real failure: app is up, DB is not reachable.
    """
    db_ok = check_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "unreachable",
    }
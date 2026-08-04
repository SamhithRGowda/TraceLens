from fastapi import FastAPI

from app.core.config import settings
from app.core.database import check_connection
from app.api.v1.events import router as events_router

app = FastAPI(title=settings.app_name)

app.include_router(events_router, prefix="/api/v1")


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

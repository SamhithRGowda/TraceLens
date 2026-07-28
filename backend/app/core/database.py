"""
Database engine + session management.

Kept separate from config.py on purpose: config.py knows *values*
(the connection string), this file knows *behavior* (how we open,
use, and close connections). That split keeps each file doing one job.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base   

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)

# Every model (Project, Trace, Evidence) inherits from this.
Base = declarative_base()   

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency: yields a session, always closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_connection() -> bool:
    """Used by the /health endpoint to verify the DB is actually reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.trace import Trace


def get_or_create_trace(db: Session, project_id: UUID, session_id: str, event_timestamp: datetime) -> Trace:
    """
    Looks up a trace by (project_id, session_id); creates it if this
    is the first evidence we've seen for this session.

    MVP simplification, stated plainly: we assume evidence arrives
    roughly in the order it happened, so on an existing trace we just
    push ended_at forward to this event's timestamp. We are not
    handling out-of-order/backfilled evidence robustly yet.
    """
    trace = (
        db.query(Trace)
        .filter(Trace.project_id == project_id, Trace.session_id == session_id)
        .first()
    )

    if trace is not None:
        trace.ended_at = event_timestamp
        db.flush()
        return trace

    trace = Trace(
        project_id=project_id,
        session_id=session_id,
        started_at=event_timestamp,
        ended_at=event_timestamp,
    )
    db.add(trace)
    db.flush()
    return trace

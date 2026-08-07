from datetime import datetime
from uuid import UUID

from sqlalchemy import func
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


def get_traces_by_ids(db: Session, trace_ids) -> list[Trace]:
    return db.query(Trace).filter(Trace.id.in_(trace_ids)).all()


def get_traces_in_time_window(db: Session, project_id: UUID, start: datetime, end: datetime) -> list[Trace]:
    """
    Traces in the same project whose time range overlaps [start, end].
    Overlap condition: the trace started before our window ends, AND
    the trace ended (or, if still "ended_at is null", started) after
    our window begins. Standard interval-overlap check.
    """
    return (
        db.query(Trace)
        .filter(
            Trace.project_id == project_id,
            Trace.started_at <= end,
            func.coalesce(Trace.ended_at, Trace.started_at) >= start,
        )
        .all()
    )

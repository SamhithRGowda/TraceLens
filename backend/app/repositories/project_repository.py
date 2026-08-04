from sqlalchemy.orm import Session

from app.models.project import Project


def get_or_create_project(db: Session, name: str) -> Project:
    """
    Looks up a project by name; creates it if it doesn't exist yet.
    This is what lets the SDK just say project="my-agent" without a
    separate registration step — see Day 4 notes on the tradeoff
    (a typo silently creates a second project).
    """
    project = db.query(Project).filter(Project.name == name).first()
    if project is not None:
        return project

    project = Project(name=name)
    db.add(project)
    db.flush()  # assigns project.id without committing the transaction yet
    return project

"""create investigations table

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "investigations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "incident_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id"),
            nullable=False,
        ),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("cited_evidence_ids", postgresql.JSONB(), nullable=False),
        sa.Column("taxonomy_version", sa.Integer(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_investigations_incident_id", "investigations", ["incident_id"])


def downgrade():
    op.drop_index("ix_investigations_incident_id", table_name="investigations")
    op.drop_table("investigations")

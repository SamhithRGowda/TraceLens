"""create remediations table

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "remediations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "investigation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investigations.id"),
            nullable=False,
        ),
        sa.Column("recommended_fix", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_remediations_investigation_id", "remediations", ["investigation_id"])


def downgrade():
    op.drop_index("ix_remediations_investigation_id", table_name="remediations")
    op.drop_table("remediations")

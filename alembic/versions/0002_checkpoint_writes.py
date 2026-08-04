"""independent checkpoint writes

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-04
"""

from alembic import op

from sdlc.persistence.models import WorkflowWriteRow


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    WorkflowWriteRow.__table__.create(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    WorkflowWriteRow.__table__.drop(bind=op.get_bind(), checkfirst=True)

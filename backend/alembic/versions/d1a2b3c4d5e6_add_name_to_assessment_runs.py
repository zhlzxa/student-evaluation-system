"""add name to assessment_runs

Revision ID: d1a2b3c4d5e6
Revises: cc3b1f5e2b42
Create Date: 2025-09-09 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d1a2b3c4d5e6"
down_revision = "7ee2dbd6253e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assessment_runs",
        sa.Column("name", sa.String(length=256), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assessment_runs", "name")



"""add agent_models_json column to assessment_runs

Revision ID: b9f2d1a7a3c1
Revises: 84f8dfef1946
Create Date: 2025-09-07 06:10:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b9f2d1a7a3c1'
down_revision = '84f8dfef1946'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add JSON column for per-run agent model overrides
    op.add_column('assessment_runs', sa.Column('agent_models_json', postgresql.JSON(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('assessment_runs', 'agent_models_json')


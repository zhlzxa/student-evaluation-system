"""
merge heads for owner_user_id and manual_decision

Revision ID: ff1e2d3c4b5a
Revises: 30bcaedbd8ac, d1a2b3c4d5e7
Create Date: 2025-09-10
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ff1e2d3c4b5a'
down_revision = ('30bcaedbd8ac', 'd1a2b3c4d5e7')
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This is a merge migration; no operations required.
    pass


def downgrade() -> None:
    # This is a merge migration; no operations required.
    pass



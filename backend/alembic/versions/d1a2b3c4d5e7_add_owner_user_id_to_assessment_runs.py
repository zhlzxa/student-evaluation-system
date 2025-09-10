"""
add owner_user_id to assessment_runs

Revision ID: d1a2b3c4d5e7
Revises: d1a2b3c4d5e6_add_name_to_assessment_runs
Create Date: 2025-09-10
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd1a2b3c4d5e7'
down_revision = 'd1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('assessment_runs', sa.Column('owner_user_id', sa.Integer(), nullable=True))
    op.create_index('ix_assessment_runs_owner_user_id', 'assessment_runs', ['owner_user_id'])
    op.create_foreign_key(
        'fk_assessment_runs_owner_user_id_users',
        'assessment_runs',
        'users',
        ['owner_user_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_assessment_runs_owner_user_id_users', 'assessment_runs', type_='foreignkey')
    op.drop_index('ix_assessment_runs_owner_user_id', table_name='assessment_runs')
    op.drop_column('assessment_runs', 'owner_user_id')



"""add run_logs table for agent tracing

Revision ID: cc3b1f5e2b42
Revises: b9f2d1a7a3c1
Create Date: 2025-09-07 06:30:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'cc3b1f5e2b42'
down_revision = 'b9f2d1a7a3c1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'run_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('run_id', sa.Integer(), sa.ForeignKey('assessment_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('applicant_id', sa.Integer(), sa.ForeignKey('applicants.id', ondelete='CASCADE'), nullable=True),
        sa.Column('agent_name', sa.String(length=64), nullable=False),
        sa.Column('phase', sa.String(length=16), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_run_logs_run_id', 'run_logs', ['run_id'])
    op.create_index('ix_run_logs_applicant_id', 'run_logs', ['applicant_id'])
    op.create_index('ix_run_logs_agent_name', 'run_logs', ['agent_name'])
    op.create_index('ix_run_logs_phase', 'run_logs', ['phase'])
    op.create_index('ix_run_logs_created_at', 'run_logs', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_run_logs_created_at', table_name='run_logs')
    op.drop_index('ix_run_logs_phase', table_name='run_logs')
    op.drop_index('ix_run_logs_agent_name', table_name='run_logs')
    op.drop_index('ix_run_logs_applicant_id', table_name='run_logs')
    op.drop_index('ix_run_logs_run_id', table_name='run_logs')
    op.drop_table('run_logs')


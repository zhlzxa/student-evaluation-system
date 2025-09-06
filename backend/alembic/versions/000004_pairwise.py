"""pairwise comparisons table

Revision ID: 000004_pairwise
Revises: 000003_evaluations
Create Date: N/A

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "000004_pairwise"
down_revision = "000003_evaluations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pairwise_comparisons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("assessment_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("applicant_a_id", sa.Integer(), sa.ForeignKey("applicants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("applicant_b_id", sa.Integer(), sa.ForeignKey("applicants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("winner", sa.String(length=4), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("pass_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_pairwise_run", "pairwise_comparisons", ["run_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_pairwise_run", table_name="pairwise_comparisons")
    op.drop_table("pairwise_comparisons")


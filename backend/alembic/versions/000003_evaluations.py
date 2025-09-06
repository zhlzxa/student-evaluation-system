"""evaluation results tables

Revision ID: 000003_evaluations
Revises: 000002_assessments
Create Date: N/A

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "000003_evaluations"
down_revision = "000002_assessments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "applicant_evaluations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("applicant_id", sa.Integer(), sa.ForeignKey("applicants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_name", sa.String(length=64), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_applicant_evaluations_applicant_id", "applicant_evaluations", ["applicant_id"], unique=False)
    op.create_index("ix_applicant_evaluations_agent", "applicant_evaluations", ["agent_name"], unique=False)

    op.create_table(
        "applicant_gating",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("applicant_id", sa.Integer(), sa.ForeignKey("applicants.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_applicant_gating_decision", "applicant_gating", ["decision"], unique=False)

    op.create_table(
        "applicant_ranking",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("applicant_id", sa.Integer(), sa.ForeignKey("applicants.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("weighted_score", sa.Float(), nullable=True),
        sa.Column("final_rank", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("applicant_ranking")
    op.drop_index("ix_applicant_gating_decision", table_name="applicant_gating")
    op.drop_table("applicant_gating")
    op.drop_index("ix_applicant_evaluations_agent", table_name="applicant_evaluations")
    op.drop_index("ix_applicant_evaluations_applicant_id", table_name="applicant_evaluations")
    op.drop_table("applicant_evaluations")


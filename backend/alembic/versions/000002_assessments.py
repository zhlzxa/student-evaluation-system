"""assessments scaffolding

Revision ID: 000002_assessments
Revises: 000001_init_rules
Create Date: N/A

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "000002_assessments"
down_revision = "000001_init_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assessment_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rule_set_id", sa.Integer(), sa.ForeignKey("admission_rule_sets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("custom_requirements", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_index("ix_assessment_runs_status", "assessment_runs", ["status"], unique=False)

    op.create_table(
        "applicants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("assessment_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=True),
        sa.Column("email", sa.String(length=256), nullable=True),
        sa.Column("folder_name", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_index("ix_applicants_run_id", "applicants", ["run_id"], unique=False)

    op.create_table(
        "applicant_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("applicant_id", sa.Integer(), sa.ForeignKey("applicants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rel_path", sa.String(length=1024), nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("text_preview", sa.Text(), nullable=True),
        sa.Column("doc_type", sa.String(length=64), nullable=True),
    )

    op.create_index("ix_applicant_documents_applicant_id", "applicant_documents", ["applicant_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_applicant_documents_applicant_id", table_name="applicant_documents")
    op.drop_table("applicant_documents")
    op.drop_index("ix_applicants_run_id", table_name="applicants")
    op.drop_table("applicants")
    op.drop_index("ix_assessment_runs_status", table_name="assessment_runs")
    op.drop_table("assessment_runs")


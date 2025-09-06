"""init rules

Revision ID: 000001_init_rules
Revises: 
Create Date: N/A

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "000001_init_rules"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "degree_equivalency_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("uk_class", sa.String(length=32), nullable=False, index=True),
        sa.Column("source_url", sa.String(length=1000), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("uk_class", name="uq_degree_equiv_source_uk_class"),
    )

    op.create_table(
        "english_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nationality_exempt_countries", sa.JSON(), nullable=True),
        sa.Column("degree_obtained_exempt_countries", sa.JSON(), nullable=True),
        sa.Column("levels", sa.JSON(), nullable=True),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "admission_rule_sets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("english_rule_id", sa.Integer(), sa.ForeignKey("english_rules.id", ondelete="SET NULL"), nullable=True),
    )

    op.create_table(
        "country_degree_equivalencies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("country_code", sa.String(length=3), nullable=False, index=True),
        sa.Column("country_name", sa.String(length=128), nullable=False, index=True),
        sa.Column("uk_class", sa.String(length=32), nullable=False, index=True),
        sa.Column("requirement", sa.JSON(), nullable=True),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("country_code", "uk_class", name="uq_country_uk_class"),
    )

    op.create_table(
        "special_institution_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("country_code", sa.String(length=3), nullable=False, index=True),
        sa.Column("institution_name", sa.String(length=512), nullable=False, index=True),
        sa.Column("category", sa.String(length=64), nullable=False, index=True),
        sa.Column("thresholds", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.UniqueConstraint("country_code", "institution_name", name="uq_country_institution"),
    )


def downgrade() -> None:
    op.drop_table("special_institution_rules")
    op.drop_table("country_degree_equivalencies")
    op.drop_table("admission_rule_sets")
    op.drop_table("english_rules")
    op.drop_table("degree_equivalency_sources")


"""add cms content table

Revision ID: 281723ba07be
Revises: 156d8781d7b8
Create Date: 2024-06-23 12:00:32.297761

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "281723ba07be"
down_revision = "056b595a6a00"
branch_labels = None
depends_on = None


def upgrade():
    cms_types_enum = sa.Enum(
        "JOKE", "QUESTION", "FACT", "QUOTE", name="enum_cms_content_type"
    )

    cms_status_enum = sa.Enum(
        "DRAFT",
        "PENDING_REVIEW",
        "APPROVED",
        "PUBLISHED",
        "ARCHIVED",
        name="enum_cms_content_status",
    )

    op.create_table(
        "cms_content",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column(
            "type",
            cms_types_enum,
            nullable=False,
        ),
        sa.Column(
            "status", cms_status_enum, server_default=sa.text("'DRAFT'"), nullable=False
        ),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "info",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_content_user", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(op.f("ix_cms_content_type"), "cms_content", ["type"], unique=False)
    op.create_index(
        op.f("ix_cms_content_status"), "cms_content", ["status"], unique=False
    )
    op.create_index(op.f("ix_cms_content_tags"), "cms_content", ["tags"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_cms_content_type"), table_name="cms_content")
    op.drop_index(op.f("ix_cms_content_id"), table_name="cms_content")
    op.drop_table("cms_content")

    op.execute("DROP TYPE enum_cms_content_type")
    genresource = sa.Enum(name="enum_cms_content_type")
    genresource.drop(op.get_bind(), checkfirst=True)

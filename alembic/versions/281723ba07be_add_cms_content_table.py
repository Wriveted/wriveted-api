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
down_revision = "156d8781d7b8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cms_content",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column(
            "type",
            sa.Enum("JOKE", "QUESTION", "FACT", "QUOTE", name="enum_cms_content_type"),
            nullable=False,
        ),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_content_user", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cms_content_id"), "cms_content", ["id"], unique=True)
    op.create_index(op.f("ix_cms_content_type"), "cms_content", ["type"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_cms_content_type"), table_name="cms_content")
    op.drop_index(op.f("ix_cms_content_id"), table_name="cms_content")
    op.drop_table("cms_content")

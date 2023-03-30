"""change info blobs to JSONB

Revision ID: 71cb2ac1c707
Revises: 671ac58d1a3d
Create Date: 2023-03-30 16:19:49.760641

"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision = "71cb2ac1c707"
down_revision = "671ac58d1a3d"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "events", "info", type_=JSONB, nullable=True, postgresql_using="info::jsonb"
    )
    op.alter_column(
        "authors", "info", type_=JSONB, nullable=True, postgresql_using="info::jsonb"
    )
    op.alter_column(
        "book_lists", "info", type_=JSONB, nullable=True, postgresql_using="info::jsonb"
    )
    op.alter_column(
        "collections",
        "info",
        type_=JSONB,
        nullable=True,
        postgresql_using="info::jsonb",
    )
    op.alter_column(
        "collection_items",
        "info",
        type_=JSONB,
        nullable=True,
        postgresql_using="info::jsonb",
    )
    op.alter_column(
        "editions", "info", type_=JSONB, nullable=True, postgresql_using="info::jsonb"
    )
    op.alter_column(
        "labelsets", "info", type_=JSONB, nullable=True, postgresql_using="info::jsonb"
    )
    op.alter_column(
        "parents",
        "parent_info",
        type_=JSONB,
        nullable=True,
        postgresql_using="parent_info::jsonb",
    )
    op.alter_column(
        "public_readers",
        "reader_info",
        type_=JSONB,
        nullable=True,
        postgresql_using="reader_info::jsonb",
    )
    op.alter_column(
        "readers", "info", type_=JSONB, nullable=True, postgresql_using="info::jsonb"
    )
    op.alter_column(
        "school_admins",
        "info",
        type_=JSONB,
        nullable=True,
        postgresql_using="info::jsonb",
    )
    op.alter_column(
        "service_accounts",
        "info",
        type_=JSONB,
        nullable=True,
        postgresql_using="info::jsonb",
    )
    op.alter_column(
        "students",
        "student_info",
        type_=JSONB,
        nullable=True,
        postgresql_using="student_info::jsonb",
    )
    op.alter_column(
        "subscriptions",
        "info",
        type_=JSONB,
        nullable=True,
        postgresql_using="info::jsonb",
    )
    op.alter_column(
        "supporters",
        "supporter_info",
        type_=JSONB,
        nullable=True,
        postgresql_using="supporter_info::jsonb",
    )
    op.alter_column(
        "users", "info", type_=JSONB, nullable=True, postgresql_using="info::jsonb"
    )
    op.alter_column(
        "works", "info", type_=JSONB, nullable=True, postgresql_using="info::jsonb"
    )
    op.alter_column(
        "wriveted_admin",
        "wriveted_admin_info",
        type_=JSONB,
        nullable=True,
        postgresql_using="wriveted_admin_info::jsonb",
    )

    # ### end Alembic commands ###


def downgrade():
    op.alter_column(
        "events", "info", type_=sa.JSON(), nullable=True, postgresql_using="info::json"
    )
    op.alter_column(
        "authors", "info", type_=sa.JSON(), nullable=True, postgresql_using="info::json"
    )
    op.alter_column(
        "book_lists",
        "info",
        type_=sa.JSON(),
        nullable=True,
        postgresql_using="info::json",
    )
    op.alter_column(
        "collections",
        "info",
        type_=sa.JSON(),
        nullable=True,
        postgresql_using="info::json",
    )
    op.alter_column(
        "collection_items",
        "info",
        type_=sa.JSON(),
        nullable=True,
        postgresql_using="info::json",
    )
    op.alter_column(
        "editions",
        "info",
        type_=sa.JSON(),
        nullable=True,
        postgresql_using="info::json",
    )
    op.alter_column(
        "labelsets",
        "info",
        type_=sa.JSON(),
        nullable=True,
        postgresql_using="info::json",
    )
    op.alter_column(
        "parents",
        "parent_info",
        type_=sa.JSON(),
        nullable=True,
        postgresql_using="parent_info::json",
    )
    op.alter_column(
        "public_readers",
        "reader_info",
        type_=sa.JSON(),
        nullable=True,
        postgresql_using="reader_info::json",
    )
    op.alter_column(
        "readers", "info", type_=sa.JSON(), nullable=True, postgresql_using="info::json"
    )
    op.alter_column(
        "school_admins",
        "info",
        type_=sa.JSON(),
        nullable=True,
        postgresql_using="info::json",
    )
    op.alter_column(
        "service_accounts",
        "info",
        type_=sa.JSON(),
        nullable=True,
        postgresql_using="info::json",
    )
    op.alter_column(
        "students",
        "student_info",
        type_=sa.JSON(),
        nullable=True,
        postgresql_using="student_info::json",
    )
    op.alter_column(
        "subscriptions",
        "info",
        type_=sa.JSON(),
        nullable=True,
        postgresql_using="info::json",
    )
    op.alter_column(
        "supporters",
        "supporter_info",
        type_=sa.JSON(),
        nullable=True,
        postgresql_using="supporter_info::json",
    )
    op.alter_column(
        "users", "info", type_=sa.JSON(), nullable=True, postgresql_using="info::json"
    )
    op.alter_column(
        "works", "info", type_=sa.JSON(), nullable=True, postgresql_using="info::json"
    )
    op.alter_column(
        "wriveted_admin",
        "wriveted_admin_info",
        type_=sa.JSON(),
        nullable=True,
        postgresql_using="wriveted_admin_info::json",
    )

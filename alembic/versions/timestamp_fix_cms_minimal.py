"""Minimal fix for CMS timestamp timezone handling

Revision ID: a9f8c2d1e3b4
Revises: c95cae956373
Create Date: 2025-09-02 20:18:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "a9f8c2d1e3b4"
down_revision = "c95cae956373"
branch_labels = None
depends_on = None


def upgrade():
    # Convert only the CMS timestamp columns to timezone-aware
    # This fixes the issue where timestamps were stored without timezone info

    # Flow definitions
    op.alter_column(
        "flow_definitions",
        "created_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
    )

    op.alter_column(
        "flow_definitions",
        "updated_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
    )

    # Flow nodes
    op.alter_column(
        "flow_nodes",
        "created_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
    )

    op.alter_column(
        "flow_nodes",
        "updated_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
    )

    # CMS content
    op.alter_column(
        "cms_content",
        "created_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
    )

    op.alter_column(
        "cms_content",
        "updated_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
    )


def downgrade():
    # Revert timezone-aware timestamps back to naive timestamps

    # CMS content
    op.alter_column(
        "cms_content",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
    )

    op.alter_column(
        "cms_content",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
    )

    # Flow nodes
    op.alter_column(
        "flow_nodes",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
    )

    op.alter_column(
        "flow_nodes",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
    )

    # Flow definitions
    op.alter_column(
        "flow_definitions",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
    )

    op.alter_column(
        "flow_definitions",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
    )

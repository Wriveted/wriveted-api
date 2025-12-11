"""make flow entry_node_id nullable

Revision ID: 18c808344c4b
Revises: a9f8c2d1e3b4
Create Date: 2025-10-22 22:53:59.636317

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "18c808344c4b"
down_revision = "a9f8c2d1e3b4"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "flow_definitions",
        "entry_node_id",
        existing_type=sa.String(length=255),
        nullable=True,
    )


def downgrade():
    op.alter_column(
        "flow_definitions",
        "entry_node_id",
        existing_type=sa.String(length=255),
        nullable=False,
    )

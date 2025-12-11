"""add_start_to_node_type_enum

Revision ID: 0ed2ef9cfe33
Revises: 9cb96e3f8574
Create Date: 2025-12-06 07:34:42.929159

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0ed2ef9cfe33"
down_revision = "9cb96e3f8574"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TYPE enum_flow_node_type ADD VALUE IF NOT EXISTS 'START' BEFORE 'MESSAGE'"
    )


def downgrade():
    pass

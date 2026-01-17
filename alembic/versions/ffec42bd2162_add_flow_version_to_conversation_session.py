"""Add flow_version to conversation_session

Revision ID: ffec42bd2162
Revises: add_exec_trace_tables
Create Date: 2025-12-13 11:15:55.595483

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "ffec42bd2162"
down_revision = "add_exec_trace_tables"
branch_labels = None
depends_on = None


def upgrade():
    # Add flow_version column to track which flow version a session ran against
    op.add_column(
        "conversation_sessions",
        sa.Column("flow_version", sa.String(length=50), nullable=True),
    )
    op.create_index(
        op.f("ix_conversation_sessions_flow_version"),
        "conversation_sessions",
        ["flow_version"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f("ix_conversation_sessions_flow_version"),
        table_name="conversation_sessions",
    )
    op.drop_column("conversation_sessions", "flow_version")

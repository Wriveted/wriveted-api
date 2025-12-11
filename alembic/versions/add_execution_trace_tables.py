"""Add execution trace tables for session replay

Revision ID: add_exec_trace_tables
Revises:
Create Date: 2025-01-15

This migration adds:
- flow_execution_steps table for storing execution traces
- trace_access_audit table for audit logging
- trace fields on conversation_sessions (trace_enabled, trace_level)
- trace fields on flow_definitions (retention_days, trace_enabled, trace_sample_rate)
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_exec_trace_tables"
down_revision = "0ed2ef9cfe33"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add trace fields to flow_definitions
    op.add_column(
        "flow_definitions",
        sa.Column(
            "retention_days",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("30"),
        ),
    )
    op.add_column(
        "flow_definitions",
        sa.Column(
            "trace_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "flow_definitions",
        sa.Column(
            "trace_sample_rate",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("100"),
        ),
    )

    # Add trace fields to conversation_sessions
    op.add_column(
        "conversation_sessions",
        sa.Column(
            "trace_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "conversation_sessions",
        sa.Column(
            "trace_level",
            sa.String(20),
            nullable=True,
            server_default=sa.text("'standard'"),
        ),
    )

    # Create flow_execution_steps table
    op.create_table(
        "flow_execution_steps",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "session_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "conversation_sessions.id",
                name="fk_exec_step_session",
                ondelete="CASCADE",
            ),
            nullable=False,
            index=True,
        ),
        sa.Column("node_id", sa.String(255), nullable=False, index=True),
        sa.Column("node_type", sa.String(50), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column(
            "state_before",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "state_after",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "execution_details",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("connection_type", sa.String(50), nullable=True),
        sa.Column("next_node_id", sa.String(255), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_details", JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    # Create indexes for flow_execution_steps
    op.create_index(
        "idx_exec_steps_session_step",
        "flow_execution_steps",
        ["session_id", "step_number"],
    )
    op.create_index(
        "idx_exec_steps_started",
        "flow_execution_steps",
        [sa.text("started_at DESC")],
    )

    # Create trace_access_audit table
    op.create_table(
        "trace_access_audit",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "session_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "conversation_sessions.id",
                name="fk_trace_audit_session",
                ondelete="CASCADE",
            ),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "accessed_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_trace_audit_user", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("access_type", sa.String(50), nullable=False),
        sa.Column(
            "accessed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            index=True,
        ),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("data_accessed", JSONB(), nullable=True),
    )


def downgrade() -> None:
    # Drop trace_access_audit table
    op.drop_table("trace_access_audit")

    # Drop indexes and flow_execution_steps table
    op.drop_index("idx_exec_steps_started", "flow_execution_steps")
    op.drop_index("idx_exec_steps_session_step", "flow_execution_steps")
    op.drop_table("flow_execution_steps")

    # Remove trace fields from conversation_sessions
    op.drop_column("conversation_sessions", "trace_level")
    op.drop_column("conversation_sessions", "trace_enabled")

    # Remove trace fields from flow_definitions
    op.drop_column("flow_definitions", "trace_sample_rate")
    op.drop_column("flow_definitions", "trace_enabled")
    op.drop_column("flow_definitions", "retention_days")

"""Add task idempotency table

Revision ID: ce87ca7a1727
Revises: 76d07c5cf3e7
Create Date: 2025-07-30 21:10:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "ce87ca7a1727"
down_revision = "76d07c5cf3e7"
branch_labels = None
depends_on = None


def upgrade():
    # Create idempotency records table
    # The enum will be created automatically by SQLAlchemy when the table is created
    op.create_table(
        "task_idempotency_records",
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PROCESSING", "COMPLETED", "FAILED", name="enum_task_execution_status"
            ),
            server_default=sa.text("'PROCESSING'"),
            nullable=False,
        ),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("node_id", sa.String(length=255), nullable=False),
        sa.Column("session_revision", sa.Integer(), nullable=False),
        sa.Column(
            "result_data",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("NULL"),
            nullable=True,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "expires_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP + INTERVAL '24 hours')"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("idempotency_key"),
    )

    # Create indexes for monitoring and performance
    op.create_index(
        op.f("ix_task_idempotency_records_idempotency_key"),
        "task_idempotency_records",
        ["idempotency_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_task_idempotency_records_session_id"),
        "task_idempotency_records",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_task_idempotency_records_status"),
        "task_idempotency_records",
        ["status"],
        unique=False,
    )


def downgrade():
    # Drop table and indexes
    op.drop_index(
        op.f("ix_task_idempotency_records_status"),
        table_name="task_idempotency_records",
    )
    op.drop_index(
        op.f("ix_task_idempotency_records_session_id"),
        table_name="task_idempotency_records",
    )
    op.drop_index(
        op.f("ix_task_idempotency_records_idempotency_key"),
        table_name="task_idempotency_records",
    )
    op.drop_table("task_idempotency_records")

    # Drop enum type
    op.execute("DROP TYPE enum_task_execution_status")

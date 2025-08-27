"""Create event outbox table

Revision ID: 572c4486f6f7
Revises: ce87ca7a1727
Create Date: 2025-08-08 23:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "572c4486f6f7"
down_revision = "ce87ca7a1727"
branch_labels = None
depends_on = None


def upgrade():
    # Create enums with unique names to avoid conflicts
    event_status_enum = postgresql.ENUM(
        "pending",
        "processing",
        "published",
        "failed",
        "dead_letter",
        name="eventoutboxstatus",
        create_type=False,  # Don't auto-create, we'll handle it manually
    )
    event_priority_enum = postgresql.ENUM(
        "low",
        "normal",
        "high",
        "critical",
        name="eventoutboxpriority",
        create_type=False,  # Don't auto-create, we'll handle it manually
    )

    # Create the enums only if they don't exist
    conn = op.get_bind()
    # Check PostgreSQL version compatibility - IF NOT EXISTS added in v9.1+
    conn.execute(
        sa.text("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'eventoutboxstatus') THEN
                CREATE TYPE eventoutboxstatus AS ENUM ('PENDING', 'PROCESSING', 'PUBLISHED', 'FAILED', 'DEAD_LETTER');
            END IF;
        END$$;
    """)
    )
    conn.execute(
        sa.text("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'eventoutboxpriority') THEN
                CREATE TYPE eventoutboxpriority AS ENUM ('LOW', 'NORMAL', 'HIGH', 'CRITICAL');
            END IF;
        END$$;
    """)
    )

    # Create event_outbox table with proper enum types
    op.create_table(
        "event_outbox",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column(
            "event_version",
            sa.String(length=20),
            server_default=sa.text("'1.0'"),
            nullable=False,
        ),
        sa.Column(
            "source_service",
            sa.String(length=50),
            server_default=sa.text("'wriveted-api'"),
            nullable=False,
        ),
        sa.Column("destination", sa.String(length=100), nullable=False),
        sa.Column("routing_key", sa.String(length=100), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("headers", sa.JSON(), nullable=True),
        sa.Column(
            "status",
            event_status_enum,
            server_default=sa.text("'PENDING'"),
            nullable=False,
        ),
        sa.Column(
            "priority",
            event_priority_enum,
            server_default=sa.text("'NORMAL'"),
            nullable=False,
        ),
        sa.Column(
            "retry_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "max_retries", sa.Integer(), server_default=sa.text("3"), nullable=False
        ),
        sa.Column("next_retry_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("error_details", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("processed_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("correlation_id", sa.String(length=100), nullable=True),
        sa.Column("causation_id", sa.String(length=100), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("session_id", sa.UUID(), nullable=True),
        sa.Column("flow_id", sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index("ix_event_outbox_event_type", "event_outbox", ["event_type"])
    op.create_index("ix_event_outbox_next_retry_at", "event_outbox", ["next_retry_at"])
    op.create_index("ix_event_outbox_priority", "event_outbox", ["priority"])
    op.create_index("ix_event_outbox_status", "event_outbox", ["status"])


def downgrade():
    # Drop indexes and table
    op.drop_index("ix_event_outbox_status", table_name="event_outbox")
    op.drop_index("ix_event_outbox_priority", table_name="event_outbox")
    op.drop_index("ix_event_outbox_next_retry_at", table_name="event_outbox")
    op.drop_index("ix_event_outbox_event_type", table_name="event_outbox")
    op.drop_table("event_outbox")

    # Drop enums
    conn = op.get_bind()
    conn.execute(sa.text("DROP TYPE IF EXISTS eventoutboxstatus"))
    conn.execute(sa.text("DROP TYPE IF EXISTS eventoutboxpriority"))

"""Add webhook_subscriptions table

Revision ID: 0e96090c57f5
Revises: ffec42bd2162
Create Date: 2026-01-09 09:22:11.610129

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "0e96090c57f5"
down_revision = "ffec42bd2162"
branch_labels = None
depends_on = None


def upgrade():
    """Create webhook_subscriptions table for reliable webhook delivery via Event Outbox."""
    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("secret", sa.String(length=255), nullable=True),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("headers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column(
            "event_types", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("flow_id", sa.UUID(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "PAUSED", "DISABLED", name="webhooksubscriptionstatus"),
            nullable=False,
        ),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False),
        sa.Column("last_success_at", sa.DateTime(), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["flow_id"], ["flow_definitions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_webhook_subscriptions_flow_id"),
        "webhook_subscriptions",
        ["flow_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_webhook_subscriptions_status"),
        "webhook_subscriptions",
        ["status"],
        unique=False,
    )


def downgrade():
    """Remove webhook_subscriptions table."""
    op.drop_index(
        op.f("ix_webhook_subscriptions_status"), table_name="webhook_subscriptions"
    )
    op.drop_index(
        op.f("ix_webhook_subscriptions_flow_id"), table_name="webhook_subscriptions"
    )
    op.drop_table("webhook_subscriptions")

    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS webhooksubscriptionstatus")

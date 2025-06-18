"""Create complete CMS and chatbot system

Revision ID: 76d07c5cf3e7
Revises: 056b595a6a00
Create Date: 2025-06-18 08:21:18.591519

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "76d07c5cf3e7"
down_revision = "056b595a6a00"
branch_labels = None
depends_on = None


def upgrade():
    # Create all enums first with their final correct names and values

    # CMS Content enums
    cms_content_type_enum = sa.Enum(
        "JOKE",
        "QUESTION",
        "FACT",
        "QUOTE",
        "MESSAGE",
        "PROMPT",
        name="enum_cms_content_type",
    )
    cms_content_status_enum = sa.Enum(
        "DRAFT",
        "PENDING_REVIEW",
        "APPROVED",
        "PUBLISHED",
        "ARCHIVED",
        name="enum_cms_content_status",
    )

    # Flow system enums
    flow_node_type_enum = sa.Enum(
        "MESSAGE",
        "QUESTION",
        "CONDITION",
        "ACTION",
        "WEBHOOK",
        "COMPOSITE",
        name="enum_flow_node_type",
    )
    flow_connection_type_enum = sa.Enum(
        "DEFAULT",
        "OPTION_0",
        "OPTION_1",
        "SUCCESS",
        "FAILURE",
        name="enum_flow_connection_type",
    )
    conversation_session_status_enum = sa.Enum(
        "ACTIVE", "COMPLETED", "ABANDONED", name="enum_conversation_session_status"
    )
    # Use correct enum name from the start
    interaction_type_enum = sa.Enum(
        "MESSAGE", "INPUT", "ACTION", name="enum_interaction_type"
    )

    # Create CMS Content table
    op.create_table(
        "cms_content",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("type", cms_content_type_enum, nullable=False),
        sa.Column(
            "status",
            cms_content_status_enum,
            server_default=sa.text("'DRAFT'"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "info",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
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
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_content_user", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # CMS Content indexes
    op.create_index(op.f("ix_cms_content_type"), "cms_content", ["type"], unique=False)
    op.create_index(
        op.f("ix_cms_content_status"), "cms_content", ["status"], unique=False
    )
    op.create_index(op.f("ix_cms_content_tags"), "cms_content", ["tags"], unique=False)
    op.create_index(
        op.f("ix_cms_content_is_active"), "cms_content", ["is_active"], unique=False
    )

    # Create Flow Definitions table
    op.create_table(
        "flow_definitions",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("flow_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("entry_node_id", sa.String(length=255), nullable=False),
        sa.Column(
            "info",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
        sa.Column(
            "is_published",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
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
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("published_by", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_flow_created_by", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["published_by"],
            ["users.id"],
            name="fk_flow_published_by",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_flow_definitions_is_active"),
        "flow_definitions",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_flow_definitions_is_published"),
        "flow_definitions",
        ["is_published"],
        unique=False,
    )

    # Create CMS Content Variants table
    op.create_table(
        "cms_content_variants",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("content_id", sa.UUID(), nullable=False),
        sa.Column("variant_key", sa.String(length=100), nullable=False),
        sa.Column(
            "variant_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "weight", sa.Integer(), server_default=sa.text("100"), nullable=False
        ),
        sa.Column(
            "conditions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
        sa.Column(
            "performance_data",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
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
        sa.ForeignKeyConstraint(
            ["content_id"],
            ["cms_content.id"],
            name="fk_variant_content",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_cms_content_variants_content_id"),
        "cms_content_variants",
        ["content_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cms_content_variants_is_active"),
        "cms_content_variants",
        ["is_active"],
        unique=False,
    )

    # Create Conversation Sessions table
    op.create_table(
        "conversation_sessions",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("flow_id", sa.UUID(), nullable=False),
        sa.Column("session_token", sa.String(length=255), nullable=False),
        sa.Column("current_node_id", sa.String(length=255), nullable=True),
        sa.Column(
            "state",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
        sa.Column(
            "info",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "last_activity_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column(
            "status",
            conversation_session_status_enum,
            server_default=sa.text("'ACTIVE'"),
            nullable=False,
        ),
        sa.Column(
            "revision", sa.Integer(), server_default=sa.text("1"), nullable=False
        ),
        sa.Column("state_hash", sa.String(length=44), nullable=True),
        sa.ForeignKeyConstraint(
            ["flow_id"],
            ["flow_definitions.id"],
            name="fk_session_flow",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_session_user", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_conversation_sessions_session_token"),
        "conversation_sessions",
        ["session_token"],
        unique=True,
    )
    op.create_index(
        op.f("ix_conversation_sessions_status"),
        "conversation_sessions",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_conversation_sessions_user_id"),
        "conversation_sessions",
        ["user_id"],
        unique=False,
    )

    # Create Flow Nodes table
    op.create_table(
        "flow_nodes",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("flow_id", sa.UUID(), nullable=False),
        sa.Column("node_id", sa.String(length=255), nullable=False),
        sa.Column("node_type", flow_node_type_enum, nullable=False),
        sa.Column("template", sa.String(length=100), nullable=True),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "position",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
        sa.Column(
            "info",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(
            ["flow_id"],
            ["flow_definitions.id"],
            name="fk_node_flow",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_flow_nodes_flow_id"), "flow_nodes", ["flow_id"], unique=False
    )
    op.create_index(
        op.f("ix_flow_nodes_node_type"), "flow_nodes", ["node_type"], unique=False
    )
    # Unique constraint for node_id within a flow
    op.create_index(
        "ix_flow_nodes_flow_node_unique",
        "flow_nodes",
        ["flow_id", "node_id"],
        unique=True,
    )

    # Create Flow Connections table
    op.create_table(
        "flow_connections",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("flow_id", sa.UUID(), nullable=False),
        sa.Column("source_node_id", sa.String(length=255), nullable=False),
        sa.Column("target_node_id", sa.String(length=255), nullable=False),
        sa.Column("connection_type", flow_connection_type_enum, nullable=False),
        sa.Column(
            "conditions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
        sa.Column(
            "info",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(
            ["flow_id"],
            ["flow_definitions.id"],
            name="fk_connection_flow",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_flow_connections_flow_id"),
        "flow_connections",
        ["flow_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_flow_connections_source_node_id"),
        "flow_connections",
        ["source_node_id"],
        unique=False,
    )

    # Create Conversation History table
    op.create_table(
        "conversation_history",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("node_id", sa.String(length=255), nullable=False),
        sa.Column("interaction_type", interaction_type_enum, nullable=False),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["conversation_sessions.id"],
            name="fk_history_session",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_conversation_history_created_at"),
        "conversation_history",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_conversation_history_session_id"),
        "conversation_history",
        ["session_id"],
        unique=False,
    )

    # Create Conversation Analytics table
    op.create_table(
        "conversation_analytics",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("flow_id", sa.UUID(), nullable=False),
        sa.Column("node_id", sa.String(length=255), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(
            ["flow_id"],
            ["flow_definitions.id"],
            name="fk_analytics_flow",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_conversation_analytics_date"),
        "conversation_analytics",
        ["date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_conversation_analytics_flow_id"),
        "conversation_analytics",
        ["flow_id"],
        unique=False,
    )

    # Create the notification function for real-time events
    op.execute("""
        CREATE OR REPLACE FUNCTION notify_flow_event()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Notify on session state changes with comprehensive event data
            IF TG_OP = 'INSERT' THEN
                PERFORM pg_notify(
                    'flow_events',
                    json_build_object(
                        'event_type', 'session_started',
                        'session_id', NEW.id,
                        'flow_id', NEW.flow_id,
                        'user_id', NEW.user_id,
                        'current_node', NEW.current_node_id,
                        'status', NEW.status,
                        'revision', NEW.revision,
                        'timestamp', extract(epoch from NEW.started_at)
                    )::text
                );
                RETURN NEW;
            ELSIF TG_OP = 'UPDATE' THEN
                -- Only notify on significant state changes
                IF OLD.current_node_id IS DISTINCT FROM NEW.current_node_id 
                   OR OLD.status IS DISTINCT FROM NEW.status 
                   OR OLD.revision IS DISTINCT FROM NEW.revision THEN
                    PERFORM pg_notify(
                        'flow_events',
                        json_build_object(
                            'event_type', CASE 
                                WHEN OLD.status IS DISTINCT FROM NEW.status THEN 'session_status_changed'
                                WHEN OLD.current_node_id IS DISTINCT FROM NEW.current_node_id THEN 'node_changed'
                                ELSE 'session_updated'
                            END,
                            'session_id', NEW.id,
                            'flow_id', NEW.flow_id,
                            'user_id', NEW.user_id,
                            'current_node', NEW.current_node_id,
                            'previous_node', OLD.current_node_id,
                            'status', NEW.status,
                            'previous_status', OLD.status,
                            'revision', NEW.revision,
                            'previous_revision', OLD.revision,
                            'timestamp', extract(epoch from NEW.last_activity_at)
                        )::text
                    );
                END IF;
                RETURN NEW;
            ELSIF TG_OP = 'DELETE' THEN
                PERFORM pg_notify(
                    'flow_events',
                    json_build_object(
                        'event_type', 'session_deleted',
                        'session_id', OLD.id,
                        'flow_id', OLD.flow_id,
                        'user_id', OLD.user_id,
                        'timestamp', extract(epoch from NOW())
                    )::text
                );
                RETURN OLD;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create the trigger on conversation_sessions
    op.execute("""
        CREATE TRIGGER conversation_sessions_notify_flow_event_trigger
            AFTER INSERT OR UPDATE OR DELETE ON conversation_sessions 
            FOR EACH ROW EXECUTE FUNCTION notify_flow_event();
    """)


def downgrade():
    # Drop trigger and function
    op.execute(
        "DROP TRIGGER IF EXISTS conversation_sessions_notify_flow_event_trigger ON conversation_sessions;"
    )
    op.execute("DROP FUNCTION IF EXISTS notify_flow_event();")

    # Drop tables in reverse dependency order
    op.drop_table("conversation_analytics")
    op.drop_table("conversation_history")
    op.drop_table("flow_connections")
    op.drop_table("flow_nodes")
    op.drop_table("conversation_sessions")
    op.drop_table("cms_content_variants")
    op.drop_table("flow_definitions")
    op.drop_table("cms_content")

    # Drop enums
    op.execute("DROP TYPE enum_interaction_type")
    op.execute("DROP TYPE enum_conversation_session_status")
    op.execute("DROP TYPE enum_flow_connection_type")
    op.execute("DROP TYPE enum_flow_node_type")
    op.execute("DROP TYPE enum_cms_content_status")
    op.execute("DROP TYPE enum_cms_content_type")

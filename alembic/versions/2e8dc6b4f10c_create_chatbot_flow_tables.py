"""Create chatbot flow tables

Revision ID: 2e8dc6b4f10c
Revises: 281723ba07be
Create Date: 2025-06-15 20:50:43.769262

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "2e8dc6b4f10c"
down_revision = "281723ba07be"
branch_labels = None
depends_on = None


def upgrade():
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
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "performance_data",
            sa.JSON(),
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
        sa.ForeignKeyConstraint(
            ["content_id"],
            ["cms_content.id"],
            name="fk_variant_content",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_id", "variant_key", name="uq_content_variant_key"),
    )
    op.create_table(
        "conversation_analytics",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("flow_id", sa.UUID(), nullable=False),
        sa.Column("node_id", sa.String(length=255), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
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
        sa.UniqueConstraint(
            "flow_id", "node_id", "date", name="uq_analytics_flow_node_date"
        ),
    )
    op.create_index(
        op.f("ix_conversation_analytics_date"),
        "conversation_analytics",
        ["date"],
        unique=False,
    )

    conversation_session_status_enum = sa.Enum(
        "ACTIVE", "COMPLETED", "ABANDONED", name="enum_conversation_session_status"
    )
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

    flow_nodes_type = sa.Enum(
        "MESSAGE",
        "QUESTION",
        "CONDITION",
        "ACTION",
        "WEBHOOK",
        "COMPOSITE",
        name="enum_flow_node_type",
    )
    op.create_table(
        "flow_nodes",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("flow_id", sa.UUID(), nullable=False),
        sa.Column("node_id", sa.String(length=255), nullable=False),
        sa.Column("node_type", flow_nodes_type, nullable=False),
        sa.Column("template", sa.String(length=100), nullable=True),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "position",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text('\'{"x": 0, "y": 0}\'::json'),
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
        sa.UniqueConstraint("flow_id", "node_id", name="uq_flow_node_id"),
    )
    op.create_index(
        op.f("ix_flow_nodes_node_type"), "flow_nodes", ["node_type"], unique=False
    )

    conversation_history_interaction_type = sa.Enum(
        "MESSAGE", "INPUT", "ACTION", name="enum_conversation_history_interaction_type"
    )
    op.create_table(
        "conversation_history",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("node_id", sa.String(length=255), nullable=False),
        sa.Column(
            "interaction_type", conversation_history_interaction_type, nullable=False
        ),
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

    flow_connection_type = sa.Enum(
        "DEFAULT",
        "OPTION_0",
        "OPTION_1",
        "SUCCESS",
        "FAILURE",
        name="enum_flow_connection_type",
    )
    op.create_table(
        "flow_connections",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("flow_id", sa.UUID(), nullable=False),
        sa.Column("source_node_id", sa.String(length=255), nullable=False),
        sa.Column("target_node_id", sa.String(length=255), nullable=False),
        sa.Column("connection_type", flow_connection_type, nullable=False),
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
        sa.ForeignKeyConstraint(
            ["flow_id", "source_node_id"],
            ["flow_nodes.flow_id", "flow_nodes.node_id"],
            name="fk_connection_source_node",
        ),
        sa.ForeignKeyConstraint(
            ["flow_id", "target_node_id"],
            ["flow_nodes.flow_id", "flow_nodes.node_id"],
            name="fk_connection_target_node",
        ),
        sa.ForeignKeyConstraint(
            ["flow_id"],
            ["flow_definitions.id"],
            name="fk_connection_flow",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "flow_id",
            "source_node_id",
            "target_node_id",
            "connection_type",
            name="uq_flow_connection",
        ),
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

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###

    op.create_index(
        op.f("ix_school_state"),
        "schools",
        [
            "country_code",
            sa.literal_column("((info -> 'location'::text) ->> 'state'::text)"),
        ],
        unique=False,
    )
    op.add_column(
        "cms_content",
        sa.Column("user_id", sa.UUID(), autoincrement=False, nullable=True),
    )
    op.drop_constraint("fk_content_created_by", "cms_content", type_="foreignkey")
    op.create_foreign_key(
        op.f("fk_content_user"),
        "cms_content",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_index(op.f("ix_cms_content_tags"), table_name="cms_content")
    op.drop_index(op.f("ix_cms_content_status"), table_name="cms_content")
    op.drop_index(op.f("ix_cms_content_is_active"), table_name="cms_content")
    op.create_index(op.f("ix_cms_content_id"), "cms_content", ["id"], unique=True)
    op.alter_column(
        "cms_content",
        "content",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
    )
    op.drop_column("cms_content", "created_by")
    op.drop_column("cms_content", "version")
    op.drop_column("cms_content", "status")
    op.drop_column("cms_content", "is_active")
    op.drop_column("cms_content", "tags")
    op.drop_column("cms_content", "info")
    op.drop_index(
        op.f("ix_flow_connections_source_node_id"), table_name="flow_connections"
    )
    op.drop_index(op.f("ix_flow_connections_flow_id"), table_name="flow_connections")
    op.drop_table("flow_connections")
    op.drop_index(
        op.f("ix_conversation_history_session_id"), table_name="conversation_history"
    )
    op.drop_index(
        op.f("ix_conversation_history_created_at"), table_name="conversation_history"
    )
    op.drop_table("conversation_history")
    op.drop_index(op.f("ix_flow_nodes_node_type"), table_name="flow_nodes")
    op.drop_table("flow_nodes")
    op.drop_index(
        op.f("ix_conversation_sessions_user_id"), table_name="conversation_sessions"
    )
    op.drop_index(
        op.f("ix_conversation_sessions_status"), table_name="conversation_sessions"
    )
    op.drop_index(
        op.f("ix_conversation_sessions_session_token"),
        table_name="conversation_sessions",
    )
    op.drop_table("conversation_sessions")
    op.drop_index(
        op.f("ix_conversation_analytics_date"), table_name="conversation_analytics"
    )
    op.drop_table("conversation_analytics")
    op.drop_table("cms_content_variants")
    op.drop_index(
        op.f("ix_flow_definitions_is_published"), table_name="flow_definitions"
    )
    op.drop_index(op.f("ix_flow_definitions_is_active"), table_name="flow_definitions")
    op.drop_table("flow_definitions")
    # ### end Alembic commands ###

    op.execute("DROP TYPE enum_conversation_session_status")
    op.execute("DROP TYPE enum_flow_node_type")
    op.execute("DROP TYPE enum_conversation_history_interaction_type")
    op.execute("DROP TYPE enum_flow_connection_type")

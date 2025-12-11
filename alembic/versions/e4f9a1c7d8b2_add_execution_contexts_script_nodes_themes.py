"""Add execution contexts, SCRIPT node type, and chat themes

Revision ID: e4f9a1c7d8b2
Revises: 18c808344c4b
Create Date: 2025-12-05 10:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "e4f9a1c7d8b2"
down_revision = "18c808344c4b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ExecutionContext enum (uppercase to match existing enum conventions)
    execution_context_enum = postgresql.ENUM(
        "FRONTEND", "BACKEND", "MIXED", name="enum_execution_context", create_type=True
    )
    execution_context_enum.create(op.get_bind())

    # Add SCRIPT to NodeType enum (uppercase to match existing enum values)
    op.execute("ALTER TYPE enum_flow_node_type ADD VALUE IF NOT EXISTS 'SCRIPT'")

    # Add execution_context column to flow_nodes
    op.add_column(
        "flow_nodes",
        sa.Column(
            "execution_context",
            sa.Enum("FRONTEND", "BACKEND", "MIXED", name="enum_execution_context"),
            nullable=False,
            server_default="BACKEND",
        ),
    )

    # Create index on execution_context for efficient filtering
    op.create_index(
        "idx_flow_nodes_execution_context",
        "flow_nodes",
        ["execution_context"],
        unique=False,
    )

    # Create chat_themes table
    op.create_table(
        "chat_themes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("school_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("logo_url", sa.String(), nullable=True),
        sa.Column("avatar_url", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("version", sa.String(), nullable=False, server_default="1.0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["school_id"],
            ["schools.wriveted_identifier"],
            name="fk_chat_themes_school_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_chat_themes_created_by",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_chat_themes"),
    )

    # Create indexes on chat_themes
    op.create_index(
        "idx_chat_themes_school_id", "chat_themes", ["school_id"], unique=False
    )
    op.create_index(
        "idx_chat_themes_is_active", "chat_themes", ["is_active"], unique=False
    )
    op.create_index(
        "idx_chat_themes_is_default", "chat_themes", ["is_default"], unique=False
    )
    op.create_index(
        "idx_chat_themes_created_by", "chat_themes", ["created_by"], unique=False
    )

    # Add theme_id column to schools table (optional theme reference)
    op.add_column(
        "schools",
        sa.Column("theme_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_schools_theme_id",
        "schools",
        "chat_themes",
        ["theme_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_schools_theme_id", "schools", ["theme_id"], unique=False)

    # Add theme_id column to flow_definitions table (optional flow-specific theme)
    op.add_column(
        "flow_definitions",
        sa.Column("theme_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_flow_definitions_theme_id",
        "flow_definitions",
        "chat_themes",
        ["theme_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "idx_flow_definitions_theme_id", "flow_definitions", ["theme_id"], unique=False
    )


def downgrade() -> None:
    # Drop theme_id columns and constraints
    op.drop_index("idx_flow_definitions_theme_id", table_name="flow_definitions")
    op.drop_constraint(
        "fk_flow_definitions_theme_id", "flow_definitions", type_="foreignkey"
    )
    op.drop_column("flow_definitions", "theme_id")

    op.drop_index("idx_schools_theme_id", table_name="schools")
    op.drop_constraint("fk_schools_theme_id", "schools", type_="foreignkey")
    op.drop_column("schools", "theme_id")

    # Drop chat_themes indexes and table
    op.drop_index("idx_chat_themes_created_by", table_name="chat_themes")
    op.drop_index("idx_chat_themes_is_default", table_name="chat_themes")
    op.drop_index("idx_chat_themes_is_active", table_name="chat_themes")
    op.drop_index("idx_chat_themes_school_id", table_name="chat_themes")
    op.drop_table("chat_themes")

    # Drop execution_context column and index
    op.drop_index("idx_flow_nodes_execution_context", table_name="flow_nodes")
    op.drop_column("flow_nodes", "execution_context")

    # Drop ExecutionContext enum
    execution_context_enum = postgresql.ENUM(
        "FRONTEND", "BACKEND", "MIXED", name="enum_execution_context"
    )
    execution_context_enum.drop(op.get_bind())

    # Note: Cannot remove 'script' from enum_flow_node_type enum in PostgreSQL
    # without recreating the enum and updating all references
    # This is acceptable as the value won't cause issues if unused

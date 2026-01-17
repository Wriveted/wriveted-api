"""fix_script_enum_case

Revision ID: 9cb96e3f8574
Revises: e4f9a1c7d8b2
Create Date: 2025-12-06 00:21:22.293704

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "9cb96e3f8574"
down_revision = "e4f9a1c7d8b2"
branch_labels = None
depends_on = None


def upgrade():
    # Fix the enum case inconsistency: 'script' -> 'SCRIPT'
    # PostgreSQL requires dropping and recreating the enum

    # Step 1: Rename the old enum
    op.execute("ALTER TYPE enum_flow_node_type RENAME TO enum_flow_node_type_old")

    # Step 2: Create new enum with correct case (all uppercase)
    op.execute("""
        CREATE TYPE enum_flow_node_type AS ENUM (
            'MESSAGE', 'QUESTION', 'CONDITION', 'ACTION', 'WEBHOOK', 'COMPOSITE', 'SCRIPT'
        )
    """)

    # Step 3: Update the column to use the new enum
    op.execute("""
        ALTER TABLE flow_nodes
        ALTER COLUMN node_type TYPE enum_flow_node_type
        USING node_type::text::enum_flow_node_type
    """)

    # Step 4: Drop the old enum
    op.execute("DROP TYPE enum_flow_node_type_old")


def downgrade():
    # Revert to lowercase 'script' if needed
    op.execute("ALTER TYPE enum_flow_node_type RENAME TO enum_flow_node_type_old")

    op.execute("""
        CREATE TYPE enum_flow_node_type AS ENUM (
            'MESSAGE', 'QUESTION', 'CONDITION', 'ACTION', 'WEBHOOK', 'COMPOSITE', 'script'
        )
    """)

    op.execute("""
        ALTER TABLE flow_nodes
        ALTER COLUMN node_type TYPE enum_flow_node_type
        USING node_type::text::enum_flow_node_type
    """)

    op.execute("DROP TYPE enum_flow_node_type_old")

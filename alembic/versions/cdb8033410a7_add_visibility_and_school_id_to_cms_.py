"""Add visibility and school_id to CMS content and flows

Revision ID: cdb8033410a7
Revises: a937b06a2d07
Create Date: 2026-01-09 16:11:51.218438

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "cdb8033410a7"
down_revision = "a937b06a2d07"
branch_labels = None
depends_on = None


def upgrade():
    # Create the ContentVisibility enum type
    content_visibility_enum = postgresql.ENUM(
        "private",
        "school",
        "public",
        "wriveted",
        name="enum_cms_content_visibility",
        create_type=False,
    )
    content_visibility_enum.create(op.get_bind(), checkfirst=True)

    # Add columns to cms_content
    op.add_column(
        "cms_content",
        sa.Column(
            "school_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "schools.wriveted_identifier",
                name="fk_content_school",
                ondelete="CASCADE",
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "cms_content",
        sa.Column(
            "visibility",
            sa.Enum(
                "private",
                "school",
                "public",
                "wriveted",
                name="enum_cms_content_visibility",
            ),
            nullable=False,
            server_default="wriveted",
        ),
    )
    op.create_index(
        op.f("ix_cms_content_school_id"),
        "cms_content",
        ["school_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cms_content_visibility"),
        "cms_content",
        ["visibility"],
        unique=False,
    )

    # Add columns to flow_definitions
    op.add_column(
        "flow_definitions",
        sa.Column(
            "school_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "schools.wriveted_identifier",
                name="fk_flow_school",
                ondelete="CASCADE",
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "flow_definitions",
        sa.Column(
            "visibility",
            sa.Enum(
                "private",
                "school",
                "public",
                "wriveted",
                name="enum_cms_content_visibility",
            ),
            nullable=False,
            server_default="wriveted",
        ),
    )
    op.create_index(
        op.f("ix_flow_definitions_school_id"),
        "flow_definitions",
        ["school_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_flow_definitions_visibility"),
        "flow_definitions",
        ["visibility"],
        unique=False,
    )


def downgrade():
    # Drop columns from flow_definitions
    op.drop_index(op.f("ix_flow_definitions_visibility"), table_name="flow_definitions")
    op.drop_index(op.f("ix_flow_definitions_school_id"), table_name="flow_definitions")
    op.drop_constraint("fk_flow_school", "flow_definitions", type_="foreignkey")
    op.drop_column("flow_definitions", "visibility")
    op.drop_column("flow_definitions", "school_id")

    # Drop columns from cms_content
    op.drop_index(op.f("ix_cms_content_visibility"), table_name="cms_content")
    op.drop_index(op.f("ix_cms_content_school_id"), table_name="cms_content")
    op.drop_constraint("fk_content_school", "cms_content", type_="foreignkey")
    op.drop_column("cms_content", "visibility")
    op.drop_column("cms_content", "school_id")

    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS enum_cms_content_visibility")

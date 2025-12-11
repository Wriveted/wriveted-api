"""
Add cms_content FTS column, index, function, and trigger (declarative alignment)

Revision ID: c95cae956373
Revises: 572c4486f6f7
Create Date: 2025-08-31 00:00:00.000000
"""

import sqlalchemy as sa
from alembic_utils.pg_function import PGFunction
from alembic_utils.pg_trigger import PGTrigger

from alembic import op

# revision identifiers, used by Alembic.
revision = "c95cae956373"
down_revision = "572c4486f6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add tsvector column (nullable; populated by trigger)
    op.add_column(
        "cms_content",
        sa.Column("search_document", sa.dialects.postgresql.TSVECTOR(), nullable=True),
    )

    # Create GIN index on search_document
    op.create_index(
        "idx_cms_content_search_document",
        "cms_content",
        [sa.text("search_document")],
        unique=False,
        postgresql_using="gin",
    )

    # Create trigger function via alembic_utils
    cms_content_tsvector_update = PGFunction(
        schema="public",
        signature="cms_content_tsvector_update()",
        definition=(
            "returns trigger LANGUAGE plpgsql\n      AS $function$\n        BEGIN\n            NEW.search_document := to_tsvector(\n                'english',\n                coalesce(NEW.content->>'text','') || ' ' ||\n                coalesce(NEW.content->>'setup','') || ' ' ||\n                coalesce(NEW.content->>'punchline','') || ' ' ||\n                coalesce(NEW.content->>'question','') || ' ' ||\n                coalesce(array_to_string(NEW.tags, ' '), '')\n            );\n            RETURN NEW;\n        END;\n      $function$\n    "
        ),
    )
    op.create_entity(cms_content_tsvector_update)

    # Create trigger via alembic_utils
    cms_content_tsvector_trigger = PGTrigger(
        schema="public",
        signature="trg_cms_content_tsvector_update",
        on_entity="public.cms_content",
        is_constraint=False,
        definition=(
            "BEFORE INSERT OR UPDATE ON public.cms_content FOR EACH ROW EXECUTE FUNCTION "
            "cms_content_tsvector_update()"
        ),
    )
    op.create_entity(cms_content_tsvector_trigger)


def downgrade() -> None:
    # Drop trigger and function
    cms_content_tsvector_trigger = PGTrigger(
        schema="public",
        signature="trg_cms_content_tsvector_update",
        on_entity="public.cms_content",
        is_constraint=False,
        definition=(
            "BEFORE INSERT OR UPDATE ON public.cms_content FOR EACH ROW EXECUTE FUNCTION "
            "cms_content_tsvector_update()"
        ),
    )
    op.drop_entity(cms_content_tsvector_trigger)

    cms_content_tsvector_update = PGFunction(
        schema="public",
        signature="cms_content_tsvector_update()",
        definition="returns trigger LANGUAGE plpgsql AS $$ $$",
    )
    op.drop_entity(cms_content_tsvector_update)

    # Drop index and column
    op.drop_index("idx_cms_content_search_document", table_name="cms_content")
    op.drop_column("cms_content", "search_document")

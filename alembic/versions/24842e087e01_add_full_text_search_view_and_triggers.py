"""Add full text search view and triggers

Revision ID: 24842e087e01
Revises: 285bafd3903a
Create Date: 2024-05-05 21:47:13.243849

"""

import sqlalchemy as sa
from alembic_utils.pg_function import PGFunction
from alembic_utils.pg_materialized_view import PGMaterializedView
from alembic_utils.pg_trigger import PGTrigger
from sqlalchemy import text as sql_text

from alembic import op

# revision identifiers, used by Alembic.
revision = "24842e087e01"
down_revision = "285bafd3903a"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    public_search_view_v1 = PGMaterializedView(
        schema="public",
        signature="search_view_v1",
        definition="SELECT w.id AS work_id,\n       a.id AS author_id,\n       s.id as series_id,\n       setweight(to_tsvector('english', coalesce(w.title, '')), 'A') ||\n       setweight(to_tsvector('english', coalesce(w.subtitle, '')), 'C') ||\n       setweight(to_tsvector('english', coalesce(a.first_name, '')), 'C') ||\n       setweight(to_tsvector('english', coalesce(a.last_name, '')), 'B') ||\n       setweight(to_tsvector('english', coalesce(s.title, '')), 'B')\n                                          AS document\nFROM public.works w\n         JOIN\n     public.author_work_association awa ON awa.work_id = w.id\n         JOIN\n     public.authors a ON a.id = awa.author_id\nLEFT JOIN\n    public.series_works_association swa ON swa.work_id = w.id\nLEFT JOIN\n    public.series s ON s.id = swa.series_id",
        with_data=True,
    )

    op.create_entity(public_search_view_v1)

    # Create a GIN index on the tsvector column 'document'
    op.create_index(
        "ix_search_document",
        "search_view_v1",
        [sa.text("document")],
        postgresql_using="gin",
    )

    public_refresh_search_view_v1_function = PGFunction(
        schema="public",
        signature="refresh_search_view_v1_function()",
        definition="returns trigger LANGUAGE plpgsql\n      AS $function$\n        BEGIN\n        REFRESH MATERIALIZED VIEW search_view_v1;\n        RETURN NEW;\n      END;\n      $function$",
    )
    op.create_entity(public_refresh_search_view_v1_function)

    public_authors_update_search_v1_from_authors_trigger = PGTrigger(
        schema="public",
        signature="update_search_v1_from_authors_trigger",
        on_entity="public.authors",
        is_constraint=False,
        definition="AFTER INSERT OR UPDATE OR DELETE ON public.authors \n    FOR EACH STATEMENT EXECUTE FUNCTION refresh_search_view_v1_function()",
    )
    op.create_entity(public_authors_update_search_v1_from_authors_trigger)

    public_works_update_search_v1_from_works_trigger = PGTrigger(
        schema="public",
        signature="update_search_v1_from_works_trigger",
        on_entity="public.works",
        is_constraint=False,
        definition="AFTER INSERT OR UPDATE OF title OR DELETE ON public.works \n    FOR EACH STATEMENT EXECUTE FUNCTION refresh_search_view_v1_function()",
    )
    op.create_entity(public_works_update_search_v1_from_works_trigger)

    public_series_update_search_v1_from_series_trigger = PGTrigger(
        schema="public",
        signature="update_search_v1_from_series_trigger",
        on_entity="public.series",
        is_constraint=False,
        definition="AFTER INSERT OR UPDATE OR DELETE ON public.series \n    FOR EACH STATEMENT EXECUTE FUNCTION refresh_search_view_v1_function()",
    )
    op.create_entity(public_series_update_search_v1_from_series_trigger)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###

    public_series_update_search_v1_from_series_trigger = PGTrigger(
        schema="public",
        signature="update_search_v1_from_series_trigger",
        on_entity="public.series",
        is_constraint=False,
        definition="AFTER INSERT OR UPDATE OR DELETE ON public.series \n    FOR EACH STATEMENT EXECUTE FUNCTION refresh_search_view_v1_function()",
    )
    op.drop_entity(public_series_update_search_v1_from_series_trigger)

    public_works_update_search_v1_from_works_trigger = PGTrigger(
        schema="public",
        signature="update_search_v1_from_works_trigger",
        on_entity="public.works",
        is_constraint=False,
        definition="AFTER INSERT OR UPDATE OF title OR DELETE ON public.works \n    FOR EACH STATEMENT EXECUTE FUNCTION refresh_search_view_v1_function()",
    )
    op.drop_entity(public_works_update_search_v1_from_works_trigger)

    public_authors_update_search_v1_from_authors_trigger = PGTrigger(
        schema="public",
        signature="update_search_v1_from_authors_trigger",
        on_entity="public.authors",
        is_constraint=False,
        definition="AFTER INSERT OR UPDATE OR DELETE ON public.authors \n    FOR EACH STATEMENT EXECUTE FUNCTION refresh_search_view_v1_function()",
    )
    op.drop_entity(public_authors_update_search_v1_from_authors_trigger)
    public_refresh_search_view_v1_function = PGFunction(
        schema="public",
        signature="refresh_search_view_v1_function()",
        definition="returns trigger LANGUAGE plpgsql\n      AS $function$\n        BEGIN\n        REFRESH MATERIALIZED VIEW search_view_v1;\n        RETURN NEW;\n      END;\n      $function$",
    )
    op.drop_entity(public_refresh_search_view_v1_function)
    op.drop_index("ix_search_document", table_name="search_view_v1")

    public_search_view_v1 = PGMaterializedView(
        schema="public",
        signature="search_view_v1",
        definition="SELECT w.id AS work_id,\n       a.id AS author_id,\n       s.id as series_id,\n       setweight(to_tsvector('english', coalesce(w.title, '')), 'A') ||\n       setweight(to_tsvector('english', coalesce(w.subtitle, '')), 'C') ||\n       setweight(to_tsvector('english', coalesce(a.first_name, '')), 'C') ||\n       setweight(to_tsvector('english', coalesce(a.last_name, '')), 'B') ||\n       setweight(to_tsvector('english', coalesce(s.title, '')), 'B')\n                                          AS document\nFROM public.works w\n         JOIN\n     public.author_work_association awa ON awa.work_id = w.id\n         JOIN\n     public.authors a ON a.id = awa.author_id\nLEFT JOIN\n    public.series_works_association swa ON swa.work_id = w.id\nLEFT JOIN\n    public.series s ON s.id = swa.series_id",
        with_data=True,
    )

    op.drop_entity(public_search_view_v1)

    # ### end Alembic commands ###

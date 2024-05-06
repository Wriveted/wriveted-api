"""Add work collection frequency view plus refresh triggers

Revision ID: 01bf3f33a0c8
Revises: 24842e087e01
Create Date: 2024-05-06 21:38:04.820324

"""

from alembic_utils.pg_function import PGFunction
from alembic_utils.pg_materialized_view import PGMaterializedView
from alembic_utils.pg_trigger import PGTrigger

from alembic import op

# revision identifiers, used by Alembic.
revision = "01bf3f33a0c8"
down_revision = "24842e087e01"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###

    op.create_index(
        op.f("ix_series_works_association_work_id"),
        "series_works_association",
        ["work_id"],
        unique=False,
    )
    public_refresh_work_collection_frequency_view_function = PGFunction(
        schema="public",
        signature="refresh_work_collection_frequency_view_function()",
        definition="returns trigger LANGUAGE plpgsql\n      AS $function$\n        BEGIN\n        REFRESH MATERIALIZED VIEW work_collection_frequency;\n        RETURN NEW;\n      END;\n      $function$",
    )
    op.create_entity(public_refresh_work_collection_frequency_view_function)

    public_work_collection_frequency = PGMaterializedView(
        schema="public",
        signature="work_collection_frequency",
        definition="SELECT\n    e.work_id,\n    SUM(ci.copies_total) AS collection_frequency\nFROM\n    public.editions e\nJOIN\n    public.collection_items ci ON ci.edition_isbn = e.isbn\nGROUP BY\n    e.work_id",
        with_data=True,
    )

    op.create_entity(public_work_collection_frequency)
    op.create_index(
        None,
        "work_collection_frequency",
        ["work_id"],
        unique=True,
    )

    public_collection_items_update_work_collection_frequency_from_collection_item_trigger = PGTrigger(
        schema="public",
        signature="update_work_collection_frequency_from_collection_item_trigger",
        on_entity="public.collection_items",
        is_constraint=False,
        definition="AFTER INSERT OR UPDATE OR DELETE ON public.collection_items \n    FOR EACH STATEMENT EXECUTE FUNCTION refresh_work_collection_frequency_view_function()",
    )
    op.create_entity(
        public_collection_items_update_work_collection_frequency_from_collection_item_trigger
    )

    public_collection_items_update_collections_trigger = PGTrigger(
        schema="public",
        signature="update_collections_trigger",
        on_entity="public.collection_items",
        is_constraint=False,
        definition="AFTER INSERT OR UPDATE ON public.collection_items FOR EACH ROW EXECUTE FUNCTION update_collections_function()",
    )
    op.drop_entity(public_collection_items_update_collections_trigger)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    public_collection_items_update_collections_trigger = PGTrigger(
        schema="public",
        signature="update_collections_trigger",
        on_entity="public.collection_items",
        is_constraint=False,
        definition="AFTER INSERT OR UPDATE ON public.collection_items FOR EACH ROW EXECUTE FUNCTION update_collections_function()",
    )
    op.create_entity(public_collection_items_update_collections_trigger)

    public_collection_items_update_work_collection_frequency_from_collection_item_trigger = PGTrigger(
        schema="public",
        signature="update_work_collection_frequency_from_collection_item_trigger",
        on_entity="public.collection_items",
        is_constraint=False,
        definition="AFTER INSERT OR UPDATE OR DELETE ON public.collection_items \n    FOR EACH STATEMENT EXECUTE FUNCTION refresh_work_collection_frequency_view_function()",
    )
    op.drop_entity(
        public_collection_items_update_work_collection_frequency_from_collection_item_trigger
    )

    public_work_collection_frequency = PGMaterializedView(
        schema="public",
        signature="work_collection_frequency",
        definition="SELECT\n    e.work_id,\n    SUM(ci.copies_total) AS collection_frequency\nFROM\n    public.editions e\nJOIN\n    public.collection_items ci ON ci.edition_isbn = e.isbn\nGROUP BY\n    e.work_id",
        with_data=True,
    )

    op.drop_entity(public_work_collection_frequency)

    public_refresh_work_collection_frequency_view_function = PGFunction(
        schema="public",
        signature="refresh_work_collection_frequency_view_function()",
        definition="returns trigger LANGUAGE plpgsql\n      AS $function$\n        BEGIN\n        REFRESH MATERIALIZED VIEW work_collection_frequency;\n        RETURN NEW;\n      END;\n      $function$",
    )
    op.drop_entity(public_refresh_work_collection_frequency_view_function)

    op.drop_index(
        op.f("ix_series_works_association_work_id"),
        table_name="series_works_association",
    )
    # ### end Alembic commands ###

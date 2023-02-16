from alembic_utils.pg_trigger import PGTrigger


class WrivetedDBTrigger(PGTrigger):
    pass


editions_update_edition_title_trigger = WrivetedDBTrigger(
    schema="public",
    signature="update_edition_title_trigger",
    on_entity="public.editions",
    is_constraint=False,
    definition="AFTER INSERT OR UPDATE OF edition_title, work_id ON public.editions FOR EACH ROW EXECUTE FUNCTION update_edition_title()",
)

works_update_edition_title_from_work_trigger = WrivetedDBTrigger(
    schema="public",
    signature="update_edition_title_from_work_trigger",
    on_entity="public.works",
    is_constraint=False,
    definition="AFTER INSERT OR UPDATE OF title ON public.works FOR EACH ROW EXECUTE FUNCTION update_edition_title_from_work()",
)

collection_items_update_collections_trigger = WrivetedDBTrigger(
    schema="public",
    signature="update_collections_trigger",
    on_entity="public.collection_items",
    is_constraint=False,
    definition="AFTER INSERT OR UPDATE ON public.collection_items FOR EACH ROW EXECUTE FUNCTION update_collections_function()",
)

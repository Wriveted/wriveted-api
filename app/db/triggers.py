from alembic_utils.pg_trigger import PGTrigger

editions_update_edition_title_trigger = PGTrigger(
    schema="public",
    signature="update_edition_title_trigger",
    on_entity="public.editions",
    is_constraint=False,
    definition="AFTER INSERT OR UPDATE OF edition_title, work_id ON public.editions FOR EACH ROW EXECUTE FUNCTION update_edition_title()",
)

works_update_edition_title_from_work_trigger = PGTrigger(
    schema="public",
    signature="update_edition_title_from_work_trigger",
    on_entity="public.works",
    is_constraint=False,
    definition="AFTER INSERT OR UPDATE OF title ON public.works FOR EACH ROW EXECUTE FUNCTION update_edition_title_from_work()",
)

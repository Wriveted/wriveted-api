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

works_update_search_v1_trigger = PGTrigger(
    schema="public",
    signature="update_search_v1_from_works_trigger",
    on_entity="public.works",
    is_constraint=False,
    definition="""
    AFTER INSERT OR UPDATE OF title OR DELETE ON public.works 
    FOR EACH STATEMENT EXECUTE FUNCTION refresh_search_view_v1_function()
    """,
)

authors_update_search_v1_trigger = PGTrigger(
    schema="public",
    signature="update_search_v1_from_authors_trigger",
    on_entity="public.authors",
    is_constraint=False,
    definition="""
    AFTER INSERT OR UPDATE OR DELETE ON public.authors 
    FOR EACH STATEMENT EXECUTE FUNCTION refresh_search_view_v1_function()
    """,
)

series_update_search_v1_trigger = PGTrigger(
    schema="public",
    signature="update_search_v1_from_series_trigger",
    on_entity="public.series",
    is_constraint=False,
    definition="""
    AFTER INSERT OR UPDATE OR DELETE ON public.series 
    FOR EACH STATEMENT EXECUTE FUNCTION refresh_search_view_v1_function()
    """,
)

from alembic_utils.pg_materialized_view import PGMaterializedView

search_view_v1 = PGMaterializedView(
    schema="public",
    signature="search_view_v1",
    definition="""
SELECT w.id AS work_id,
       jsonb_agg(a.id) AS author_ids,
       s.id as series_id,
       setweight(to_tsvector('english', coalesce(w.title, '')), 'A') ||
       setweight(to_tsvector('english', coalesce(w.subtitle, '')), 'C') ||
       setweight(to_tsvector('english', (SELECT string_agg(coalesce(first_name || ' ' || last_name, ''), ' ') FROM public.authors WHERE id IN (SELECT author_id FROM public.author_work_association WHERE work_id = w.id))), 'C') ||
       setweight(to_tsvector('english', coalesce(s.title, '')), 'B')
                                          AS document
FROM public.works w
         JOIN
     public.author_work_association awa ON awa.work_id = w.id
         JOIN
     public.authors a ON a.id = awa.author_id
LEFT JOIN
    public.series_works_association swa ON swa.work_id = w.id
LEFT JOIN
    public.series s ON s.id = swa.series_id
GROUP BY
    w.id, s.id
    """,
    with_data=True,
)

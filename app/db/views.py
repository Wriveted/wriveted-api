from alembic_utils.pg_materialized_view import PGMaterializedView

search_view_v1 = PGMaterializedView(
    schema="public",
    signature="search_view_v1",
    definition="""
SELECT w.id AS work_id,
       a.id AS author_id,
       s.id as series_id,
       setweight(to_tsvector('english', coalesce(w.title, '')), 'A') ||
       setweight(to_tsvector('english', coalesce(w.subtitle, '')), 'C') ||
       setweight(to_tsvector('english', coalesce(a.first_name, '')), 'C') ||
       setweight(to_tsvector('english', coalesce(a.last_name, '')), 'B') ||
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
    """,
    with_data=True,
)

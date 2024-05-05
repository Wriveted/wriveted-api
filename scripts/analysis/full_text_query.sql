-- The view
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
    w.id, s.id;


-- A Full Text Query using the above
select
    w.id,
    fts.author_ids,
    s.id,
    --w.title,
    ts_headline('english', coalesce(w.title, ''), plainto_tsquery('english', :query)) AS title_headline,
    ts_headline('english', coalesce(w.subtitle, ''), plainto_tsquery('english', :query)) AS subtitle_headline,
    json_agg(ts_headline('english', coalesce(a.first_name, '') || ' ' || coalesce(a.last_name, ''), plainto_tsquery('english', :query))) AS author_headlines,
    ts_headline('english', coalesce(s.title, ''), plainto_tsquery('english', :query)) AS series_title_headline,
    --fts.document doc
    ts_rank(document, websearch_to_tsquery(:query)) as rank
from search_view_v1 fts
join works w on w.id = fts.work_id
JOIN
     public.author_work_association awa ON awa.work_id = w.id
         JOIN
     public.authors a ON a.id = ANY(ARRAY(SELECT jsonb_array_elements_text(fts.author_ids)::int))
LEFT JOIN
    public.series_works_association swa ON swa.work_id = w.id
LEFT JOIN
    public.series s ON s.id = swa.series_id
where
    document @@ websearch_to_tsquery('english', :query)
group by
    w.id, fts.author_ids, s.id, fts.document
order by
    rank desc
;
select
    w.id,
    a.id,
    s.id,
    --w.title,
    ts_headline('english', coalesce(w.title, ''), plainto_tsquery('english', :query)) AS title_headline,
    ts_headline('english', coalesce(w.subtitle, ''), plainto_tsquery('english', :query)) AS subtitle_headline,
    ts_headline('english', coalesce(a.first_name, ''), plainto_tsquery('english', :query)) AS first_name_headline,
    ts_headline('english', coalesce(a.last_name, ''), plainto_tsquery('english', :query)) AS last_name_headline,
    ts_headline('english', coalesce(s.title, ''), plainto_tsquery('english', :query)) AS series_title_headline,
    --fts.document doc
    ts_rank(document, websearch_to_tsquery(:query)) as rank
from search_view_v1 fts
join works w on w.id = fts.work_id
JOIN
     public.author_work_association awa ON awa.work_id = w.id
         JOIN
     public.authors a ON a.id = awa.author_id
LEFT JOIN
    public.series_works_association swa ON swa.work_id = w.id
LEFT JOIN
    public.series s ON s.id = swa.series_id
where
    document @@ websearch_to_tsquery('english', :query)
order by rank desc
;
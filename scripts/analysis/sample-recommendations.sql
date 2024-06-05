

SELECT *
FROM labelsets
TABLESAMPLE BERNOULLI (1)  -- 1% of the rows randomly selected
WHERE recommend_status = 'GOOD'
limit 1000;

--
CREATE EXTENSION tsm_system_rows;

SELECT *
FROM labelsets
TABLESAMPLE system_rows (:limit)
WHERE recommend_status = 'GOOD'
;



explain analyse WITH sampled_labelsets AS (
    SELECT id, work_id
    FROM labelsets
    TABLESAMPLE system_rows (2000)
    WHERE recommend_status = 'GOOD'

),
latest_labelsets AS (
    SELECT DISTINCT ON (work_id) id, work_id
    FROM sampled_labelsets
    ORDER BY work_id, id DESC
),
latest_editions AS (
    SELECT DISTINCT ON (work_id) id, work_id
    FROM editions
    ORDER BY work_id, id DESC
)
SELECT w.*, e.*
FROM latest_labelsets ls
JOIN latest_editions e ON ls.work_id = e.work_id
JOIN works w ON w.id = ls.work_id;
;


with
    selected_schools as (
        select * from schools where wriveted_identifier = :q
    ),
    selected_collections as (
        select * from collections where school_id = (select wriveted_identifier from selected_schools)
    ),
    collection_isbns as (
        select edition_isbn from collection_items where collection_id in (select id from selected_collections)
    ),
    works as (
        select
            e.isbn,
            e.work_id,
            e.title
        from editions e
    ),
    collection_works as (
        select
            ci.edition_isbn,
            w.work_id,
            w.title as title
        from works w
        join collection_isbns ci on ci.edition_isbn = w.isbn
    ),
    latest_labelsets AS (
        SELECT DISTINCT ON (work_id) id, work_id
        FROM labelsets
    ),
    labelset_work_ids_for_collection_works as (
        select
            ls.*
        from latest_labelsets ls
        join collection_works cw on ls.work_id = cw.work_id
    ),
    labelsets_for_collection_works as (
        select
            ls.*
        from labelset_work_ids_for_collection_works lw
        join labelsets ls on lw.id = ls.id
        limit 10000
    )


-- Not fast enough!
SELECT * from labelsets_for_collection_works order by random() limit 10;

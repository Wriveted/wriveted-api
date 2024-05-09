
-- Given a School's Wriveted ID show the most liked books in the collection

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
    book_liked_events as (
        select
            timestamp,
            info->>'isbn' as isbn
            --info
        from events e
        where e.title = 'Huey: Book reviewed' and
              e.school_id = (select id from selected_schools) and
              info->>'liked' = 'true'
    ),
    -- Group the liked events by ISBN
    book_like_count as (
        select
            isbn,
            count(isbn) as liked_count
        from book_liked_events
        group by isbn
    ),
    -- Show the number works liked (not necessarily in the collection)
    liked_works as (select w.work_id,
                           w.title,
                           coalesce(bl.liked_count, 0) as liked_count
                    from works w
                             left join book_like_count bl on bl.isbn = w.isbn
                    order by liked_count desc),
    -- Show the number of likes for each book in the collection
    collection_liked_works as (
        select
            cw.work_id,
            cw.title,
            coalesce(bl.liked_count, 0) as liked_count
        from collection_works cw
        left join book_like_count bl on bl.isbn = cw.edition_isbn
        order by liked_count desc
    )


--select * from collection_works limit 10;
--select * from book_like_count  limit 10;
select * from liked_works limit 100;
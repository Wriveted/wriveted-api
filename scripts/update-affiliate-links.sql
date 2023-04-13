
create or replace function encode_uri_component(text) returns text as $$
    select string_agg(
        case
            when bytes > 1 or c !~ '[0-9a-zA-Z_.!~*''()-]+' then
                regexp_replace(encode(convert_to(c, 'utf-8')::bytea, 'hex'), '(..)', E'%\\1', 'g')
            else
                c
        end,
        ''
    )
    from (
        select c, octet_length(c) bytes
        from regexp_split_to_table($1, '') c
    ) q;
$$ language sql immutable strict;

-- -- craft the search term
-- select
--     concat(
--             'https://www.amazon.com.au/s?k=',
--             encode_uri_component(coalesce(edition_title, works.title)),
--             '&i=stripbooks&tag=hueybooks0a-22'
--     ) as searchterm,
--
--     editions.info->'links' as links
-- from editions, works
-- where isbn='9781760150426'
-- and editions.work_id = works.id;

-- Now how to update it?
-- In this query, we first create a WITH clause to calculate the new search term. Then, we use a
-- subquery within the jsonb_set function to create the new JSON array with the updated search term.
-- Finally, we update the editions table with the new JSON object.

WITH new_searchterm AS (
  SELECT
    editions.id as id,
    concat(
      'https://www.amazon.com.au/s?k=',
      encode_uri_component(coalesce(edition_title, works.title, isbn)::text),
      '&i=stripbooks&tag=hueybooks0a-22'
    ) AS searchterm
  FROM
    editions,
    works
  WHERE
    editions.work_id = works.id
)

    UPDATE editions
    SET info = jsonb_set(
      info::jsonb,
      '{links}',
      (
        SELECT
          jsonb_build_array(
            jsonb_build_object(
              'type', 'retailer',
              'url', new_searchterm.searchterm,
              'retailer', 'Amazon AU'
            )
          )
        FROM
          new_searchterm
        WHERE
            new_searchterm.id = editions.id
      )
    )
    WHERE
        editions.cover_url is not null;
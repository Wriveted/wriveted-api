from alembic_utils.pg_function import PGFunction

public_encode_uri_component = PGFunction(
    schema="public",
    signature="encode_uri_component(text)",
    definition="returns text\n LANGUAGE sql\n IMMUTABLE STRICT\nAS $function$\n    select string_agg(\n        case\n            when bytes > 1 or c !~ '[0-9a-zA-Z_.!~*''()-]+' then\n                regexp_replace(encode(convert_to(c, 'utf-8')::bytea, 'hex'), '(..)', E'%\\\\1', 'g')\n            else\n                c\n        end,\n        ''\n    )\n    from (\n        select c, octet_length(c) bytes\n        from regexp_split_to_table($1, '') c\n    ) q;\n$function$",
)

update_edition_title = PGFunction(
    schema="public",
    signature="update_edition_title()",
    definition="""returns trigger LANGUAGE plpgsql
    AS $function$
    BEGIN
    UPDATE editions SET title = COALESCE(editions.edition_title, works.title)
    FROM works
    WHERE editions.id = NEW.id AND (NEW.edition_title IS NOT NULL OR NEW.work_id IS NOT NULL);
    RETURN NULL;
    END;
    $function$
    """,
)

update_edition_title_from_work = PGFunction(
    schema="public",
    signature="update_edition_title_from_work()",
    definition="""returns trigger LANGUAGE plpgsql
    AS $function$
    BEGIN
        UPDATE editions SET title = COALESCE(editions.edition_title, works.title)
        FROM works
        WHERE editions.work_id = NEW.id AND (NEW.title IS NOT NULL);
        RETURN NULL;
    END;
    $function$""",
)

update_collections_function = PGFunction(
    schema="public",
    signature="update_collections_function()",
    definition="""returns trigger LANGUAGE plpgsql
      AS $function$
        BEGIN
        UPDATE collections
        SET updated_at = NOW()
        WHERE collections.id = NEW.collection_id;
        RETURN NEW;
      END;
      $function$
    """,
)

refresh_search_view_v1_function = PGFunction(
    schema="public",
    signature="refresh_search_view_v1_function()",
    definition="""returns trigger LANGUAGE plpgsql
      AS $function$
        BEGIN
        REFRESH MATERIALIZED VIEW search_view_v1;
        RETURN NEW;
      END;
      $function$
    """,
)

refresh_work_collection_frequency_view_function = PGFunction(
    schema="public",
    signature="refresh_work_collection_frequency_view_function()",
    definition="""returns trigger LANGUAGE plpgsql
      AS $function$
        BEGIN
        REFRESH MATERIALIZED VIEW work_collection_frequency;
        RETURN NEW;
      END;
      $function$
    """,
)

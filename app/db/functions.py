from alembic_utils.pg_function import PGFunction

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

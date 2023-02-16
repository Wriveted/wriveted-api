from alembic_utils.pg_function import PGFunction


class WrivetedDBFunction(PGFunction):
    pass


update_edition_title = PGFunction(
    schema="public",
    signature="update_edition_title()",
    definition="returns trigger\n LANGUAGE plpgsql\nAS $function$\n    BEGIN\n        UPDATE editions SET title = COALESCE(editions.edition_title, works.title)\n        FROM works\n        WHERE editions.work_id = works.id AND (NEW.edition_title IS NOT NULL OR NEW.work_id IS NOT NULL);\n        RETURN NULL;\n    END;\n    $function$",
)

update_edition_title_from_work = PGFunction(
    schema="public",
    signature="update_edition_title_from_work()",
    definition="returns trigger\n LANGUAGE plpgsql\nAS $function$\n    BEGIN\n        UPDATE editions SET title = COALESCE(editions.edition_title, works.title)\n        FROM works\n        WHERE editions.work_id = works.id AND (NEW.title IS NOT NULL);\n        RETURN NULL;\n    END;\n    $function$",
)

update_collections_function = WrivetedDBFunction(
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

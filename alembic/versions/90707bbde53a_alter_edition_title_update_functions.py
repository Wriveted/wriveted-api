"""Alter edition title update functions

Revision ID: 90707bbde53a
Revises: 3cc9f3831b7b
Create Date: 2023-02-17 13:51:13.443568

"""

from alembic_utils.pg_function import PGFunction

from alembic import op

# revision identifiers, used by Alembic.
revision = "90707bbde53a"
down_revision = "3cc9f3831b7b"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    public_update_edition_title = PGFunction(
        schema="public",
        signature="update_edition_title()",
        definition="returns trigger LANGUAGE plpgsql\n    AS $function$\n    BEGIN\n    UPDATE editions SET title = COALESCE(editions.edition_title, works.title)\n    FROM works\n    WHERE editions.id = NEW.id AND (NEW.edition_title IS NOT NULL OR NEW.work_id IS NOT NULL);\n    RETURN NULL;\n    END;\n    $function$",
    )
    op.replace_entity(public_update_edition_title)

    public_update_edition_title_from_work = PGFunction(
        schema="public",
        signature="update_edition_title_from_work()",
        definition="returns trigger LANGUAGE plpgsql\n    AS $function$\n    BEGIN\n        UPDATE editions SET title = COALESCE(editions.edition_title, works.title)\n        FROM works\n        WHERE editions.work_id = NEW.id AND (NEW.title IS NOT NULL);\n        RETURN NULL;\n    END;\n    $function$",
    )
    op.replace_entity(public_update_edition_title_from_work)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    public_update_edition_title_from_work = PGFunction(
        schema="public",
        signature="update_edition_title_from_work()",
        definition="returns trigger\n LANGUAGE plpgsql\nAS $function$\n    BEGIN\n        UPDATE editions SET title = COALESCE(editions.edition_title, works.title)\n        FROM works\n        WHERE editions.work_id = works.id AND (NEW.title IS NOT NULL);\n        RETURN NULL;\n    END;\n    $function$",
    )
    op.replace_entity(public_update_edition_title_from_work)
    public_update_edition_title = PGFunction(
        schema="public",
        signature="update_edition_title()",
        definition="returns trigger\n LANGUAGE plpgsql\nAS $function$\n    BEGIN\n        UPDATE editions SET title = COALESCE(editions.edition_title, works.title)\n        FROM works\n        WHERE editions.work_id = works.id AND (NEW.edition_title IS NOT NULL OR NEW.work_id IS NOT NULL);\n        RETURN NULL;\n    END;\n    $function$",
    )
    op.replace_entity(public_update_edition_title)
    # ### end Alembic commands ###

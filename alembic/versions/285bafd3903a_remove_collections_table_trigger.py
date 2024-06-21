"""Remove collections table trigger

Revision ID: 285bafd3903a
Revises: 71cb2ac1c707
Create Date: 2024-04-20 13:32:54.231456

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "285bafd3903a"
down_revision = "71cb2ac1c707"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "illustrators",
        "info",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
    )
    op.alter_column(
        "schools",
        "info",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
    )
    op.alter_column(
        "series",
        "info",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
    )
    # public_collection_items_update_collections_trigger = PGTrigger(
    #     schema="public",
    #     signature="update_collections_trigger",
    #     on_entity="public.collection_items",
    #     is_constraint=False,
    #     definition="AFTER INSERT OR UPDATE ON public.collection_items FOR EACH ROW EXECUTE FUNCTION update_collections_function()",
    # )
    # op.drop_entity(public_collection_items_update_collections_trigger)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    # public_collection_items_update_collections_trigger = PGTrigger(
    #     schema="public",
    #     signature="update_collections_trigger",
    #     on_entity="public.collection_items",
    #     is_constraint=False,
    #     definition="AFTER INSERT OR UPDATE ON public.collection_items FOR EACH ROW EXECUTE FUNCTION update_collections_function()",
    # )
    # op.create_entity(public_collection_items_update_collections_trigger)

    op.alter_column(
        "series",
        "info",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        type_=postgresql.JSON(astext_type=sa.Text()),
        existing_nullable=True,
    )
    op.alter_column(
        "schools",
        "info",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        type_=postgresql.JSON(astext_type=sa.Text()),
        existing_nullable=True,
    )
    op.alter_column(
        "illustrators",
        "info",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        type_=postgresql.JSON(astext_type=sa.Text()),
        existing_nullable=True,
    )
    # ### end Alembic commands ###

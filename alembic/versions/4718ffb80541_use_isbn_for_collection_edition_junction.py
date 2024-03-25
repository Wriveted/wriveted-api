"""Use isbn for collection:edition junction

Revision ID: 4718ffb80541
Revises: b943f85ccc3d
Create Date: 2022-02-22 20:10:00.259782

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "4718ffb80541"
down_revision = "b943f85ccc3d"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "collection_items",
        sa.Column("edition_isbn", sa.String(length=200), nullable=False),
    )
    op.drop_index("index_editions_per_collection", table_name="collection_items")
    op.create_index(
        "index_editions_per_collection",
        "collection_items",
        ["school_id", "edition_isbn"],
        unique=True,
    )
    op.drop_constraint(
        "fk_collection_items_edition_id", "collection_items", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_collection_items_edition_isbn",
        "collection_items",
        "editions",
        ["edition_isbn"],
        ["isbn"],
    )
    op.drop_column("collection_items", "edition_id")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "collection_items",
        sa.Column("edition_id", sa.INTEGER(), autoincrement=False, nullable=False),
    )
    op.drop_constraint(
        "fk_collection_items_edition_isbn", "collection_items", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_collection_items_edition_id",
        "collection_items",
        "editions",
        ["edition_id"],
        ["id"],
    )
    op.drop_index("index_editions_per_collection", table_name="collection_items")
    op.create_index(
        "index_editions_per_collection",
        "collection_items",
        ["school_id", "edition_id"],
        unique=False,
    )
    op.drop_column("collection_items", "edition_isbn")
    # ### end Alembic commands ###

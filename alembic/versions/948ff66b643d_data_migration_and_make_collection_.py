"""Data migration and make collection items required

Revision ID: 948ff66b643d
Revises: 7b43e9a90443
Create Date: 2022-01-03 12:15:33.797460

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.

revision = "948ff66b643d"
down_revision = "7b43e9a90443"
branch_labels = None
depends_on = None


def upgrade():
    # bind = op.get_bind()
    # session = orm.Session(bind=bind)

    # stmt = (
    #     update(CollectionItem)
    #         .values(copies_available=1, copies_on_loan=0)
    #     )
    # session.execute(stmt)
    # session.commit()

    # Now alter the table
    op.alter_column(
        "collection_items",
        "copies_available",
        existing_type=sa.INTEGER(),
        nullable=False,
    )
    op.alter_column(
        "collection_items", "copies_on_loan", existing_type=sa.INTEGER(), nullable=False
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "collection_items", "copies_on_loan", existing_type=sa.INTEGER(), nullable=True
    )
    op.alter_column(
        "collection_items",
        "copies_available",
        existing_type=sa.INTEGER(),
        nullable=True,
    )
    # ### end Alembic commands ###

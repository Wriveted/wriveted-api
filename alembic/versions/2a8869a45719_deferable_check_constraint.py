"""Deferable check constraint

Revision ID: 2a8869a45719
Revises: b7bcf77d3502
Create Date: 2022-06-04 21:15:58.536911

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "2a8869a45719"
down_revision = "b7bcf77d3502"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint(
        "ck_booklist_order",
        "book_list_works",
        ["booklist_id", "order_id"],
        deferrable="True",
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint("ck_booklist_order", "book_list_works", type_="unique")
    # ### end Alembic commands ###

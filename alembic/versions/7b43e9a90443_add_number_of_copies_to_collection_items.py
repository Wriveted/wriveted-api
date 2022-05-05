"""Add number of copies to collection items

Revision ID: 7b43e9a90443
Revises: 4dcb25d599e7
Create Date: 2022-01-03 12:13:56.367591

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "7b43e9a90443"
down_revision = "4dcb25d599e7"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "collection_items", sa.Column("copies_available", sa.Integer(), nullable=True)
    )
    op.add_column(
        "collection_items", sa.Column("copies_on_loan", sa.Integer(), nullable=True)
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("collection_items", "copies_on_loan")
    op.drop_column("collection_items", "copies_available")
    # ### end Alembic commands ###

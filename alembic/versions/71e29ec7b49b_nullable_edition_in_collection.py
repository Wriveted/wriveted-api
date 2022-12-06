"""nullable edition in collection

Revision ID: 71e29ec7b49b
Revises: 95df158f258b
Create Date: 2022-12-05 16:32:53.192398

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "71e29ec7b49b"
down_revision = "95df158f258b"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "collection_items",
        "edition_isbn",
        existing_type=sa.VARCHAR(length=200),
        nullable=True,
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute("DELETE FROM collection_items WHERE edition_isbn IS NULL")
    op.alter_column(
        "collection_items",
        "edition_isbn",
        existing_type=sa.VARCHAR(length=200),
        nullable=False,
    )
    # ### end Alembic commands ###

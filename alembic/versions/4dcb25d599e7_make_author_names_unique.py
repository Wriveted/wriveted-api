"""Make Author names unique

Revision ID: 4dcb25d599e7
Revises: 216e481b3c6e
Create Date: 2021-12-30 17:02:41.720791

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4dcb25d599e7"
down_revision = "216e481b3c6e"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint("authors_full_name_unique", "authors", ["full_name"])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint("authors_full_name_unique", "authors", type_="unique")
    # ### end Alembic commands ###

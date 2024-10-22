"""Promote edition:date_published to column

Revision ID: dd5c99007a29
Revises: 3b1027ac115a
Create Date: 2022-03-07 00:20:13.375763

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "dd5c99007a29"
down_revision = "3b1027ac115a"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("editions", sa.Column("date_published", sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("editions", "date_published")
    # ### end Alembic commands ###

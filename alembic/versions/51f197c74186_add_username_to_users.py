"""add username to users

Revision ID: 51f197c74186
Revises: d8b758fccb45
Create Date: 2022-05-19 01:14:02.592364

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "51f197c74186"
down_revision = "d8b758fccb45"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("users", sa.Column("username", sa.String(), nullable=True))
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_column("users", "username")
    # ### end Alembic commands ###

"""Additional indexing on users

Revision ID: ad2bcbab60ae
Revises: 4eacf29f9751
Create Date: 2022-03-17 15:59:45.866102

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "ad2bcbab60ae"
down_revision = "4eacf29f9751"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index(
        op.f("ix_users_school_id_as_admin"),
        "users",
        ["school_id_as_admin"],
        unique=False,
    )
    op.create_index(
        op.f("ix_users_school_id_as_student"),
        "users",
        ["school_id_as_student"],
        unique=False,
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_users_school_id_as_student"), table_name="users")
    op.drop_index(op.f("ix_users_school_id_as_admin"), table_name="users")
    # ### end Alembic commands ###
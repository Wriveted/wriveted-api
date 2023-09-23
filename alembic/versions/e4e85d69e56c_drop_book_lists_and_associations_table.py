"""Drop book_lists and associations table

Revision ID: e4e85d69e56c
Revises: a6743b88da5b
Create Date: 2022-04-18 12:39:42.442824

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "e4e85d69e56c"
down_revision = "a6743b88da5b"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("booklist_work_association")
    op.drop_table("book_lists")
    op.execute("drop type listtype")


def downgrade():
    pass

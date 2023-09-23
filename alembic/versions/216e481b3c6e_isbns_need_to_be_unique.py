"""ISBNs need to be unique

Revision ID: 216e481b3c6e
Revises: 48c28918b620
Create Date: 2021-12-30 14:05:21.594732

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "216e481b3c6e"
down_revision = "48c28918b620"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("ix_editions_ISBN", table_name="editions")
    op.create_index(op.f("ix_editions_ISBN"), "editions", ["ISBN"], unique=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_editions_ISBN"), table_name="editions")
    op.create_index("ix_editions_ISBN", "editions", ["ISBN"], unique=False)
    # ### end Alembic commands ###

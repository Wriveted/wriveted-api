"""add timestamps

Revision ID: 78f7fcab5df6
Revises: 02359e5f3163
Create Date: 2022-01-27 21:19:18.657389

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "78f7fcab5df6"
down_revision = "02359e5f3163"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "book_lists",
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.add_column(
        "labelsets",
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("labelsets", "created_at")
    op.drop_column("book_lists", "created_at")
    # ### end Alembic commands ###

"""Add info column to hues

Revision ID: 00f9ceaa60e5
Revises: 9a25e9984332
Create Date: 2022-07-18 16:20:33.802656

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "00f9ceaa60e5"
down_revision = "9a25e9984332"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "hues",
        sa.Column("info", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("hues", "info")
    # ### end Alembic commands ###

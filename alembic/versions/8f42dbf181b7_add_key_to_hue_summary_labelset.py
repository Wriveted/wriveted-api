"""Add key to Hue and Summary to labelset

Revision ID: 8f42dbf181b7
Revises: 292dc9c0f018
Create Date: 2022-03-09 12:08:53.420179

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "8f42dbf181b7"
down_revision = "292dc9c0f018"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("hues", sa.Column("key", sa.String(length=50), nullable=False))
    op.drop_index("ix_hues_name", table_name="hues")
    op.create_index(op.f("ix_hues_key"), "hues", ["key"], unique=True)
    op.create_unique_constraint("uq_hues_name", "hues", ["name"])
    op.add_column("labelsets", sa.Column("huey_summary", sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("labelsets", "huey_summary")
    op.drop_constraint("uq_hues_name", "hues", type_="unique")
    op.drop_index(op.f("ix_hues_key"), table_name="hues")
    op.create_index("ix_hues_name", "hues", ["name"], unique=False)
    op.drop_column("hues", "key")
    # ### end Alembic commands ###

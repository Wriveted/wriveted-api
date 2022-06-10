"""add info blob to labelset

Revision ID: f264220c678f
Revises: b461011fb4fc
Create Date: 2022-01-19 17:54:49.397954

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "f264220c678f"
down_revision = "b461011fb4fc"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("labelsets", sa.Column("info", sa.JSON(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("labelsets", "info")
    # ### end Alembic commands ###

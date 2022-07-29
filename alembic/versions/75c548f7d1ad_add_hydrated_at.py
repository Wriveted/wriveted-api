"""add hydrated_at

Revision ID: 75c548f7d1ad
Revises: e3788a1248a5
Create Date: 2022-07-13 19:08:47.630684

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "75c548f7d1ad"
down_revision = "e3788a1248a5"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("editions", sa.Column("hydrated_at", sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("editions", "hydrated_at")
    # ### end Alembic commands ###
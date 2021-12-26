"""Add primary works boolean to series

Revision ID: 8db19b335b7e
Revises: a7f1942d3ae5
Create Date: 2021-12-27 10:51:12.707427

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8db19b335b7e'
down_revision = 'a7f1942d3ae5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('series_works_association', sa.Column('primary_works', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('series_works_association', 'primary_works')
    # ### end Alembic commands ###

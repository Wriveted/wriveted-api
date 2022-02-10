"""Add newsletter bool to user

Revision ID: 9e12a1313cce
Revises: 9aeaa2d68970
Create Date: 2022-02-10 17:56:08.844262

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9e12a1313cce'
down_revision = '9aeaa2d68970'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('newsletter', sa.Boolean(), server_default='false', nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'newsletter')
    # ### end Alembic commands ###

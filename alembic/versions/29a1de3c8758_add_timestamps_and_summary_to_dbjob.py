"""add timestamps and summary to dbjob

Revision ID: 29a1de3c8758
Revises: 972df5f95c74
Create Date: 2022-01-20 17:07:22.646991

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '29a1de3c8758'
down_revision = '972df5f95c74'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('db_jobs', sa.Column('summary', sa.JSON(), nullable=True))
    op.add_column('db_jobs', sa.Column('created_timestamp', sa.DateTime(), nullable=True))
    op.add_column('db_jobs', sa.Column('started_timestamp', sa.DateTime(), nullable=True))
    op.add_column('db_jobs', sa.Column('ended_timestamp', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('db_jobs', 'ended_timestamp')
    op.drop_column('db_jobs', 'started_timestamp')
    op.drop_column('db_jobs', 'created_timestamp')
    op.drop_column('db_jobs', 'summary')
    # ### end Alembic commands ###

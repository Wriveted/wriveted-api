"""add db job relationships

Revision ID: 972df5f95c74
Revises: 0b1e21c0df91
Create Date: 2022-01-19 20:49:45.131006

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '972df5f95c74'
down_revision = '0b1e21c0df91'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('events', sa.Column('db_job_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_event_db_job', 'events', 'db_jobs', ['db_job_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('fk_event_db_job', 'events', type_='foreignkey')
    op.drop_column('events', 'db_job_id')
    # ### end Alembic commands ###

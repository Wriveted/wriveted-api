"""Add json index for state to schools

Revision ID: c3c83bc3f558
Revises: e59c3ceb5830
Create Date: 2022-02-03 17:04:29.158115

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3c83bc3f558'
down_revision = 'e59c3ceb5830'
branch_labels = None
depends_on = None


def upgrade():
    #
    op.execute("create index ix_school_state on schools using btree (country_code, (info->'location'->>'state'))")
    #


def downgrade():
    #
    op.drop_index('ix_school_state', table_name='schools')
    #

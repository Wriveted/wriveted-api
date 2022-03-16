"""Additional indexing on labelsets

Revision ID: 4eacf29f9751
Revises: 57c40ea9ffa7
Create Date: 2022-03-17 11:27:49.898340

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4eacf29f9751'
down_revision = '57c40ea9ffa7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index('index_age_range', 'labelsets', ['min_age', 'max_age'], unique=False, postgresql_where=sa.text('min_age IS NOT NULL AND max_age IS NOT NULL'))
    op.create_index('index_good_recommendations', 'labelsets', ['recommend_status'], unique=False, postgresql_where=sa.text("recommend_status = 'GOOD'"))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('index_good_recommendations', table_name='labelsets', postgresql_where=sa.text("recommend_status = 'GOOD'"))
    op.drop_index('index_age_range', table_name='labelsets', postgresql_where=sa.text('min_age IS NOT NULL AND max_age IS NOT NULL'))
    # ### end Alembic commands ###

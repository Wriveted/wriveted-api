"""update cascade logic on collection items

Revision ID: f7e6dc77ee86
Revises: 6cf4a18a99ed
Create Date: 2023-01-18 20:39:33.692814

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f7e6dc77ee86'
down_revision = '6cf4a18a99ed'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('fk_collection_item_activity_collection_item_id', 'collection_item_activity_log', type_='foreignkey')
    op.create_foreign_key('fk_collection_item_activity_collection_item_id', 'collection_item_activity_log', 'collection_items', ['collection_item_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('fk_collection_items_edition_isbn', 'collection_items', type_='foreignkey')
    op.create_foreign_key('fk_collection_items_edition_isbn', 'collection_items', 'editions', ['edition_isbn'], ['isbn'], ondelete='CASCADE')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('fk_collection_items_edition_isbn', 'collection_items', type_='foreignkey')
    op.create_foreign_key('fk_collection_items_edition_isbn', 'collection_items', 'editions', ['edition_isbn'], ['isbn'])
    op.drop_constraint('fk_collection_item_activity_collection_item_id', 'collection_item_activity_log', type_='foreignkey')
    op.create_foreign_key('fk_collection_item_activity_collection_item_id', 'collection_item_activity_log', 'collection_items', ['collection_item_id'], ['id'])
    # ### end Alembic commands ###

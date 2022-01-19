"""Add user and events tables

Revision ID: 998f29940cbf
Revises: adfec3fd4e72
Create Date: 2021-12-28 11:18:08.916902

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '998f29940cbf'
down_revision = 'adfec3fd4e72'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('users',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('school_id', sa.Integer(), nullable=True),
    sa.Column('is_superuser', sa.Boolean(), nullable=True),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('info', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['school_id'], ['schools.id'], name='fk_event_school'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=True)
    op.create_table('events',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('school_id', sa.Integer(), nullable=True),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('level', sa.Enum('DEBUG', 'NORMAL', 'WARNING', 'ERROR', name='eventlevel'), nullable=False),
    sa.Column('title', sa.String(length=256), nullable=False),
    sa.Column('description', sa.String(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['school_id'], ['schools.id'], name='fk_event_school'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_event_user'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_events_level'), 'events', ['level'], unique=False)
    op.drop_index('ix_collection_items_work_id', table_name='collection_items')
    op.drop_constraint('fk_collection_items_work_id', 'collection_items', type_='foreignkey')
    op.drop_column('collection_items', 'work_id')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('collection_items', sa.Column('work_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key('fk_collection_items_work_id', 'collection_items', 'works', ['work_id'], ['id'])
    op.create_index('ix_collection_items_work_id', 'collection_items', ['work_id'], unique=False)
    op.drop_index(op.f('ix_events_level'), table_name='events')
    op.drop_table('events')
    op.execute("DROP TYPE eventlevel")
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')

    # ### end Alembic commands ###

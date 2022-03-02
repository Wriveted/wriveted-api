"""remove full_name from authors and illustrators

Revision ID: 2976a4ff1b24
Revises: 30dc05860e78
Create Date: 2022-02-21 13:46:11.835725

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2976a4ff1b24'
down_revision = '30dc05860e78'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('authors_full_name_unique', 'authors', type_='unique')
    op.drop_constraint('authors_name_key_key', 'authors', type_='unique')
    op.create_index(op.f('ix_authors_name_key'), 'authors', ['name_key'], unique=True)
    op.drop_column('authors', 'full_name')
    op.alter_column('illustrators', 'first_name',
               existing_type=sa.VARCHAR(length=200),
               nullable=False)
    op.drop_constraint('illustrators_full_name_key', 'illustrators', type_='unique')
    op.drop_constraint('illustrators_name_key_key', 'illustrators', type_='unique')
    op.create_index(op.f('ix_illustrators_first_name'), 'illustrators', ['first_name'], unique=False)
    op.create_index(op.f('ix_illustrators_last_name'), 'illustrators', ['last_name'], unique=False)
    op.create_index(op.f('ix_illustrators_name_key'), 'illustrators', ['name_key'], unique=True)
    op.drop_column('illustrators', 'full_name')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('illustrators', sa.Column('full_name', sa.VARCHAR(length=400), sa.Computed("(COALESCE(((first_name)::text || ' '::text), ''::text) || (last_name)::text)", persisted=True), autoincrement=False, nullable=True))
    op.drop_index(op.f('ix_illustrators_name_key'), table_name='illustrators')
    op.drop_index(op.f('ix_illustrators_last_name'), table_name='illustrators')
    op.drop_index(op.f('ix_illustrators_first_name'), table_name='illustrators')
    op.create_unique_constraint('illustrators_name_key_key', 'illustrators', ['name_key'])
    op.create_unique_constraint('illustrators_full_name_key', 'illustrators', ['full_name'])
    op.alter_column('illustrators', 'first_name',
               existing_type=sa.VARCHAR(length=200),
               nullable=True)
    op.add_column('authors', sa.Column('full_name', sa.VARCHAR(length=400), autoincrement=False, nullable=False))
    op.drop_index(op.f('ix_authors_name_key'), table_name='authors')
    op.create_unique_constraint('authors_name_key_key', 'authors', ['name_key'])
    op.create_unique_constraint('authors_full_name_unique', 'authors', ['full_name'])
    # ### end Alembic commands ###
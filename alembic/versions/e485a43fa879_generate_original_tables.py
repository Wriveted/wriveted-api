"""Generate original tables

Revision ID: e485a43fa879
Revises: 
Create Date: 2021-12-23 17:23:48.776237

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e485a43fa879'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('authors',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('first_name', sa.String(length=200), nullable=True),
    sa.Column('last_name', sa.String(length=200), nullable=False),
    sa.Column('full_name', sa.String(length=400), sa.Computed("COALESCE(first_name || ' ', '') || last_name", ), nullable=True),
    sa.Column('info', sa.JSON(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('illustrators',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('first_name', sa.String(length=200), nullable=True),
    sa.Column('last_name', sa.String(length=200), nullable=False),
    sa.Column('full_name', sa.String(length=400), sa.Computed("COALESCE(first_name || ' ', '') || last_name", ), nullable=True),
    sa.Column('info', sa.JSON(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('series',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('title', sa.String(length=100), nullable=False),
    sa.Column('info', sa.JSON(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('works',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('type', sa.Enum('BOOK', 'PODCAST', name='worktype'), nullable=False),
    sa.Column('series_id', sa.String(length=36), nullable=True),
    sa.Column('title', sa.String(length=100), nullable=False),
    sa.Column('info', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['series_id'], ['series.id'], name='FK_Editions_Works'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('author_work_association',
    sa.Column('work_id', sa.String(length=36), nullable=True),
    sa.Column('author_id', sa.String(length=36), nullable=True),
    sa.ForeignKeyConstraint(['author_id'], ['authors.id'], ),
    sa.ForeignKeyConstraint(['work_id'], ['works.id'], )
    )
    op.create_table('editions',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('work_id', sa.String(length=36), nullable=False),
    sa.Column('ISBN', sa.String(length=200), nullable=False),
    sa.Column('cover_url', sa.String(length=200), nullable=False),
    sa.Column('info', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['work_id'], ['works.id'], name='FK_Editions_Works'),
    sa.PrimaryKeyConstraint('id', 'work_id'),
    sa.UniqueConstraint('id')
    )
    op.create_table('illustrator_edition_association',
    sa.Column('edition_id', sa.String(length=36), nullable=True),
    sa.Column('work_id', sa.String(length=36), nullable=True),
    sa.Column('illustrator_id', sa.String(length=36), nullable=True),
    sa.ForeignKeyConstraint(['edition_id'], ['editions.id'], ),
    sa.ForeignKeyConstraint(['illustrator_id'], ['illustrators.id'], ),
    sa.ForeignKeyConstraint(['work_id'], ['works.id'], )
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('illustrator_edition_association')
    op.drop_table('editions')
    op.drop_table('author_work_association')
    op.drop_table('works')
    op.drop_table('series')
    op.drop_table('illustrators')
    op.drop_table('authors')
    # ### end Alembic commands ###

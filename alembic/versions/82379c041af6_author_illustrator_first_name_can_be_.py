"""Author/Illustrator first name can be null

Revision ID: 82379c041af6
Revises: 3c1e2888884d
Create Date: 2022-03-08 21:35:12.784536

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '82379c041af6'
down_revision = '3c1e2888884d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('authors', 'first_name',
               existing_type=sa.VARCHAR(length=200),
               nullable=True)
    op.alter_column('illustrators', 'first_name',
               existing_type=sa.VARCHAR(length=200),
               nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('illustrators', 'first_name',
               existing_type=sa.VARCHAR(length=200),
               nullable=False)
    op.alter_column('authors', 'first_name',
               existing_type=sa.VARCHAR(length=200),
               nullable=False)
    # ### end Alembic commands ###

"""Bump up some string sizes

Revision ID: b19f3360a95b
Revises: f61643916398
Create Date: 2022-03-10 02:27:41.141393

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "b19f3360a95b"
down_revision = "f61643916398"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "genres",
        "name",
        existing_type=sa.VARCHAR(length=50),
        type_=sa.String(length=128),
        existing_nullable=False,
    )
    op.alter_column(
        "hues",
        "name",
        existing_type=sa.VARCHAR(length=50),
        type_=sa.String(length=128),
        existing_nullable=False,
    )
    op.alter_column(
        "reading_abilities",
        "name",
        existing_type=sa.VARCHAR(length=50),
        type_=sa.String(length=128),
        existing_nullable=False,
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "reading_abilities",
        "name",
        existing_type=sa.String(length=128),
        type_=sa.VARCHAR(length=50),
        existing_nullable=False,
    )
    op.alter_column(
        "hues",
        "name",
        existing_type=sa.String(length=128),
        type_=sa.VARCHAR(length=50),
        existing_nullable=False,
    )
    op.alter_column(
        "genres",
        "name",
        existing_type=sa.String(length=128),
        type_=sa.VARCHAR(length=50),
        existing_nullable=False,
    )
    # ### end Alembic commands ###

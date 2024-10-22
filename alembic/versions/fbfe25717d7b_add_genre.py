"""add genre

Revision ID: fbfe25717d7b
Revises: 29a1de3c8758
Create Date: 2022-01-21 10:59:18.217857

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "fbfe25717d7b"
down_revision = "29a1de3c8758"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "genres",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_genres_name"), "genres", ["name"], unique=True)
    op.create_table(
        "labelset_genre_association",
        sa.Column("labelset_id", sa.Integer(), nullable=False),
        sa.Column("hue_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["hue_id"], ["genres.id"], name="fk_labelset_genre_association_genre_id"
        ),
        sa.ForeignKeyConstraint(
            ["labelset_id"],
            ["labelsets.id"],
            name="fk_labelset_genre_association_labelset_id",
        ),
        sa.PrimaryKeyConstraint("labelset_id", "hue_id"),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("labelset_genre_association")
    op.drop_index(op.f("ix_genres_name"), table_name="genres")
    op.drop_table("genres")
    # ### end Alembic commands ###

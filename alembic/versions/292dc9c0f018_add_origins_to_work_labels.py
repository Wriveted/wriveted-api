"""Add origins to work labels

Revision ID: 292dc9c0f018
Revises: b007a39a80cf
Create Date: 2022-03-09 10:38:39.182004

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "292dc9c0f018"
down_revision = "b007a39a80cf"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    labelorigin = sa.Enum(
        "HUMAN",
        "PREDICTED_NIELSEN",
        "CLUSTER_RELEVANCE",
        "CLUSTER_ZAINAB",
        "OTHER",
        name="labelorigin",
    )
    labelorigin.create(op.get_bind(), checkfirst=True)
    op.add_column("labelsets", sa.Column("hue_origin", labelorigin, nullable=True))
    op.add_column(
        "labelsets", sa.Column("reading_ability_origin", labelorigin, nullable=True)
    )
    op.add_column("labelsets", sa.Column("age_origin", labelorigin, nullable=True))
    op.add_column(
        "labelsets", sa.Column("recommend_status_origin", labelorigin, nullable=True)
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("labelsets", "recommend_status_origin")
    op.drop_column("labelsets", "age_origin")
    op.drop_column("labelsets", "reading_ability_origin")
    op.drop_column("labelsets", "hue_origin")
    op.execute("DROP TYPE labelorigin")
    labelorigin = sa.Enum(name="labelorigin")
    labelorigin.drop(op.get_bind(), checkfirst=True)
    # ### end Alembic commands ###

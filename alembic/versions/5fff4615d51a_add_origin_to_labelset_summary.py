"""Add origin to labelset summary

Revision ID: 5fff4615d51a
Revises: 8f42dbf181b7
Create Date: 2022-03-09 14:12:02.795383

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "5fff4615d51a"
down_revision = "8f42dbf181b7"
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
    op.add_column("labelsets", sa.Column("summary_origin", labelorigin, nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("labelsets", "summary_origin")
    # Others columns in labelsets table still rely on this enum
    # op.execute("DROP TYPE labelorigin")
    # ### end Alembic commands ###

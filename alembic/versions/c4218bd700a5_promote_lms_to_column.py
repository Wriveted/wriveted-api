"""Promote lms to column

Revision ID: c4218bd700a5
Revises: 7a347c5cd18e
Create Date: 2022-02-09 07:38:52.101071

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c4218bd700a5"
down_revision = "7a347c5cd18e"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "schools",
        sa.Column(
            "lms_type", sa.String(length=50), server_default="none", nullable=False
        ),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("schools", "lms_type")
    # ### end Alembic commands ###

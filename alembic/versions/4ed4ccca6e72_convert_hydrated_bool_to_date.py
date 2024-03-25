"""convert hydrated bool to date

Revision ID: 4ed4ccca6e72
Revises: 75c548f7d1ad
Create Date: 2022-07-13 19:19:17.889397

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "4ed4ccca6e72"
down_revision = "75c548f7d1ad"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute("UPDATE editions SET hydrated_at = NOW() where hydrated = true")
    op.drop_column("editions", "hydrated")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "editions",
        sa.Column("hydrated", sa.BOOLEAN(), autoincrement=False, nullable=True),
    )
    op.execute("commit")
    op.execute("UPDATE editions SET hydrated = true where hydrated_at is not null")
    # ### end Alembic commands ###

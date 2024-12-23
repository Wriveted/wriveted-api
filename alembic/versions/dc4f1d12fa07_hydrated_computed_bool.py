"""hydrated computed bool

Revision ID: dc4f1d12fa07
Revises: 4ed4ccca6e72
Create Date: 2022-07-13 20:25:23.647263

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "dc4f1d12fa07"
down_revision = "4ed4ccca6e72"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "editions",
        sa.Column(
            "hydrated",
            sa.Boolean(),
            sa.Computed(
                "hydrated_at is not null",
            ),
            nullable=True,
        ),
    )
    op.create_index(
        op.f("ix_editions_hydrated"), "editions", ["hydrated"], unique=False
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_editions_hydrated"), table_name="editions")
    op.drop_column("editions", "hydrated")
    # ### end Alembic commands ###

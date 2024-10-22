"""computed name_key for authors and illustrators

Revision ID: 30dc05860e78
Revises: ea7b2dd2b6de
Create Date: 2022-02-21 12:55:38.760937

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "30dc05860e78"
down_revision = "ea7b2dd2b6de"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "authors",
        sa.Column(
            "name_key",
            sa.String(length=400),
            sa.Computed(
                "LOWER(REGEXP_REPLACE(first_name || last_name, '\\W|_', '', 'g'))",
            ),
            nullable=True,
        ),
    )
    op.create_unique_constraint("uq_authors_name_key", "authors", ["name_key"])
    op.add_column(
        "illustrators",
        sa.Column(
            "name_key",
            sa.String(length=400),
            sa.Computed(
                "LOWER(REGEXP_REPLACE(first_name || last_name, '\\W|_', '', 'g'))",
            ),
            nullable=True,
        ),
    )
    op.create_unique_constraint(
        "uq_illustrators_name_key", "illustrators", ["name_key"]
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint("uq_illustrators_name_key", "illustrators", type_="unique")
    op.drop_column("illustrators", "name_key")
    op.drop_constraint("uq_authors_name_key", "authors", type_="unique")
    op.drop_column("authors", "name_key")
    # ### end Alembic commands ###

"""make class names unique per school

Revision ID: 90aeb305955e
Revises: c761d2031a93
Create Date: 2022-06-06 11:54:38.718108

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "90aeb305955e"
down_revision = "c761d2031a93"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint(
        "unique_class_name_per_school", "class_groups", ["name", "school_id"]
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint("unique_class_name_per_school", "class_groups", type_="unique")
    # ### end Alembic commands ###
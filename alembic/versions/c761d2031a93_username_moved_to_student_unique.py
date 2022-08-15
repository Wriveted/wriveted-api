"""username moved to student, with composite unique against school

Revision ID: c761d2031a93
Revises: ad9c27e61dfa
Create Date: 2022-06-06 10:51:47.223048

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "c761d2031a93"
down_revision = "ad9c27e61dfa"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("ix_readers_username", table_name="readers")
    op.drop_column("readers", "username")
    op.add_column("students", sa.Column("username", sa.String(), nullable=False))
    op.create_index(
        op.f("ix_students_username"), "students", ["username"], unique=False
    )
    op.create_unique_constraint(
        "unique_student_username_per_school", "students", ["username", "school_id"]
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint("unique_student_username_per_school", "students", type_="unique")
    op.drop_index(op.f("ix_students_username"), table_name="students")
    op.drop_column("students", "username")
    op.add_column(
        "readers",
        sa.Column("username", sa.VARCHAR(), autoincrement=False, nullable=True),
    )
    op.create_index("ix_readers_username", "readers", ["username"], unique=False)
    # ### end Alembic commands ###

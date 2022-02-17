"""Allow longer school names

Revision ID: adfec3fd4e72
Revises: ca2a50e230f9
Create Date: 2021-12-28 08:31:20.118309

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "adfec3fd4e72"
down_revision = "ca2a50e230f9"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "schools",
        "official_identifier",
        existing_type=sa.VARCHAR(length=64),
        type_=sa.String(length=512),
        existing_nullable=True,
    )
    op.alter_column(
        "schools",
        "name",
        existing_type=sa.VARCHAR(length=100),
        type_=sa.String(length=256),
        existing_nullable=False,
    )
    op.alter_column(
        "schools",
        "student_domain",
        existing_type=sa.VARCHAR(length=100),
        type_=sa.String(length=256),
        existing_nullable=True,
    )
    op.alter_column(
        "schools",
        "teacher_domain",
        existing_type=sa.VARCHAR(length=100),
        type_=sa.String(length=256),
        existing_nullable=True,
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "schools",
        "teacher_domain",
        existing_type=sa.String(length=256),
        type_=sa.VARCHAR(length=100),
        existing_nullable=True,
    )
    op.alter_column(
        "schools",
        "student_domain",
        existing_type=sa.String(length=256),
        type_=sa.VARCHAR(length=100),
        existing_nullable=True,
    )
    op.alter_column(
        "schools",
        "name",
        existing_type=sa.String(length=256),
        type_=sa.VARCHAR(length=100),
        existing_nullable=False,
    )
    op.alter_column(
        "schools",
        "official_identifier",
        existing_type=sa.String(length=512),
        type_=sa.VARCHAR(length=64),
        existing_nullable=True,
    )
    # ### end Alembic commands ###

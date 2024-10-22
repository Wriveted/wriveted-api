"""add db jobs

Revision ID: 0b1e21c0df91
Revises: f264220c678f
Create Date: 2022-01-19 20:49:16.569146

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "0b1e21c0df91"
down_revision = "f264220c678f"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "db_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "job_type", sa.Enum("POPULATE", "UPDATE", name="jobtype"), nullable=False
        ),
        sa.Column(
            "job_status",
            sa.Enum("PENDING", "RUNNING", "COMPLETE", name="jobstatus"),
            nullable=False,
        ),
        sa.Column("total_items", sa.Integer(), nullable=True),
        sa.Column("successes", sa.Integer(), nullable=True),
        sa.Column("errors", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("db_jobs")
    op.execute("DROP TYPE jobtype")
    op.execute("DROP TYPE jobstatus")
    # ### end Alembic commands ###

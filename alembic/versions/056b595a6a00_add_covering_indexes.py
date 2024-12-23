"""Add covering indexes

Revision ID: 056b595a6a00
Revises: 156d8781d7b8
Create Date: 2024-07-27 10:09:23.909935

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "056b595a6a00"
down_revision = "156d8781d7b8"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index(
        "ix_events_service",
        "events",
        ["service_account_id"],
        unique=False,
        postgresql_where=sa.text("service_account_id IS NOT NULL"),
    )
    op.create_index(
        "ix_labelset_service_account_id",
        "labelsets",
        ["labelled_by_sa_id"],
        unique=False,
        postgresql_where=sa.text("labelled_by_sa_id IS NOT NULL"),
    )
    op.create_index(
        "ix_labelset_user_id",
        "labelsets",
        ["labelled_by_user_id"],
        unique=False,
        postgresql_where=sa.text("labelled_by_user_id IS NOT NULL"),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(
        "ix_labelset_user_id",
        table_name="labelsets",
        postgresql_where=sa.text("labelled_by_user_id IS NOT NULL"),
    )
    op.drop_index(
        "ix_labelset_service_account_id",
        table_name="labelsets",
        postgresql_where=sa.text("labelled_by_sa_id IS NOT NULL"),
    )
    op.drop_index(
        "ix_events_service",
        table_name="events",
        postgresql_where=sa.text("service_account_id IS NOT NULL"),
    )
    # ### end Alembic commands ###
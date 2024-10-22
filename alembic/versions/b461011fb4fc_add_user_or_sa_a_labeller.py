"""add user or service accounts as a labelset's labeller

Revision ID: b461011fb4fc
Revises: 427891a30fee
Create Date: 2022-01-19 16:26:19.248731

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "b461011fb4fc"
down_revision = "427891a30fee"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "labelsets",
        sa.Column("labelled_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "labelsets",
        sa.Column("labelled_by_sa_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.drop_constraint("fk_labeller_labelset", "labelsets", type_="foreignkey")
    op.create_foreign_key(
        "fk_labeller-sa_labelset",
        "labelsets",
        "service_accounts",
        ["labelled_by_sa_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_labeller-user_labelset",
        "labelsets",
        "users",
        ["labelled_by_user_id"],
        ["id"],
    )
    op.drop_column("labelsets", "labelled_by_id")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "labelsets",
        sa.Column(
            "labelled_by_id", postgresql.UUID(), autoincrement=False, nullable=True
        ),
    )
    op.drop_constraint("fk_labeller-user_labelset", "labelsets", type_="foreignkey")
    op.drop_constraint("fk_labeller-sa_labelset", "labelsets", type_="foreignkey")
    op.create_foreign_key(
        "fk_labeller_labelset", "labelsets", "users", ["labelled_by_id"], ["id"]
    )
    op.drop_column("labelsets", "labelled_by_sa_id")
    op.drop_column("labelsets", "labelled_by_user_id")
    # ### end Alembic commands ###

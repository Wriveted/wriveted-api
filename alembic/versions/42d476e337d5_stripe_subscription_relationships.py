"""stripe subscription + relationships

Revision ID: 42d476e337d5
Revises: 71e29ec7b49b
Create Date: 2022-12-11 15:52:04.786674

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "42d476e337d5"
down_revision = "71e29ec7b49b"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "stripe_subscriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stripe_customer_id", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("info", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_user_stripe_subscription"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_stripe_subscriptions_stripe_customer_id"),
        "stripe_subscriptions",
        ["stripe_customer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_stripe_subscriptions_user_id"),
        "stripe_subscriptions",
        ["user_id"],
        unique=False,
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(
        op.f("ix_stripe_subscriptions_user_id"), table_name="stripe_subscriptions"
    )
    op.drop_index(
        op.f("ix_stripe_subscriptions_stripe_customer_id"),
        table_name="stripe_subscriptions",
    )
    op.drop_table("stripe_subscriptions")
    # ### end Alembic commands ###

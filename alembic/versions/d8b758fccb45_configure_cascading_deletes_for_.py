"""Configure cascading deletes for booklists

Revision ID: d8b758fccb45
Revises: d0009439d3ac
Create Date: 2022-04-18 19:17:42.125896

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d8b758fccb45"
down_revision = "d0009439d3ac"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        "fk_booklist_items_work_id", "book_list_works", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_booklist_items_booklist_id", "book_list_works", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_booklist_items_work_id",
        "book_list_works",
        "works",
        ["work_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_booklist_items_booklist_id",
        "book_list_works",
        "book_lists",
        ["booklist_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint("fk_booklist_service_account", "book_lists", type_="foreignkey")
    op.drop_constraint("fk_booklist_school", "book_lists", type_="foreignkey")
    op.drop_constraint("fk_booklist_user", "book_lists", type_="foreignkey")
    op.create_foreign_key(
        "fk_booklist_service_account",
        "book_lists",
        "service_accounts",
        ["service_account_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_booklist_school",
        "book_lists",
        "schools",
        ["school_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_booklist_user",
        "book_lists",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint("fk_booklist_user", "book_lists", type_="foreignkey")
    op.drop_constraint("fk_booklist_school", "book_lists", type_="foreignkey")
    op.drop_constraint("fk_booklist_service_account", "book_lists", type_="foreignkey")
    op.create_foreign_key(
        "fk_booklist_user", "book_lists", "users", ["user_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_booklist_school", "book_lists", "schools", ["school_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_booklist_service_account",
        "book_lists",
        "service_accounts",
        ["service_account_id"],
        ["id"],
    )
    op.drop_constraint(
        "fk_booklist_items_booklist_id", "book_list_works", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_booklist_items_work_id", "book_list_works", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_booklist_items_booklist_id",
        "book_list_works",
        "book_lists",
        ["booklist_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_booklist_items_work_id", "book_list_works", "works", ["work_id"], ["id"]
    )
    # ### end Alembic commands ###

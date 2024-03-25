"""add booklists and relationships

Revision ID: ff8873658f55
Revises: fbfe25717d7b
Create Date: 2022-01-21 11:41:20.715886

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "ff8873658f55"
down_revision = "fbfe25717d7b"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "book_lists",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "WISH_LIST",
                "HAS_READ",
                "SCHOOL",
                "REGION_LIST",
                "HUEY_LIST",
                "OTHER_LIST",
                name="listtype",
            ),
            nullable=False,
        ),
        sa.Column("info", sa.JSON(), nullable=True),
        sa.Column("school_id", sa.Integer(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("service_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["school_id"], ["schools.id"], name="fk_booklist_school"
        ),
        sa.ForeignKeyConstraint(
            ["service_account_id"],
            ["service_accounts.id"],
            name="fk_booklist_service_account",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_booklist_user"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_book_lists_name"), "book_lists", ["name"], unique=False)
    op.create_table(
        "booklist_work_association",
        sa.Column("work_id", sa.Integer(), nullable=False),
        sa.Column("booklist_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["booklist_id"],
            ["book_lists.id"],
            name="fk_booklist_works_association_booklist_id",
        ),
        sa.ForeignKeyConstraint(
            ["work_id"], ["works.id"], name="fk_booklist_works_association_work_id"
        ),
        sa.PrimaryKeyConstraint("work_id", "booklist_id"),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("booklist_work_association")
    op.drop_index(op.f("ix_book_lists_name"), table_name="book_lists")
    op.drop_table("book_lists")
    op.execute("DROP TYPE listtype")
    # ### end Alembic commands ###

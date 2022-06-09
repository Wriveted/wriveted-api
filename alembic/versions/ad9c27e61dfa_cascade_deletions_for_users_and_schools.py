"""Cascade deletions for users and schools

Revision ID: ad9c27e61dfa
Revises: 2a8869a45719
Create Date: 2022-06-05 08:18:50.087153

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "ad9c27e61dfa"
down_revision = "2a8869a45719"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint("fk_class_groups_school", "class_groups", type_="foreignkey")
    op.create_foreign_key(
        "fk_class_groups_school",
        "class_groups",
        "schools",
        ["school_id"],
        ["wriveted_identifier"],
        ondelete="CASCADE",
    )
    op.drop_constraint("fk_educator_school", "educators", type_="foreignkey")
    op.drop_constraint("fk_educator_inherits_user", "educators", type_="foreignkey")
    op.create_foreign_key(
        "fk_educator_school",
        "educators",
        "schools",
        ["school_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_educator_inherits_user",
        "educators",
        "users",
        ["id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint("fk_parent_inherits_user", "parents", type_="foreignkey")
    op.create_foreign_key(
        "fk_parent_inherits_user",
        "parents",
        "users",
        ["id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        "fk_public_reader_inherits_reader", "public_readers", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_public_reader_inherits_reader",
        "public_readers",
        "readers",
        ["id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint("fk_reader_inherits_user", "readers", type_="foreignkey")
    op.create_foreign_key(
        "fk_reader_inherits_user",
        "readers",
        "users",
        ["id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        "fk_school_admin_inherits_educator", "school_admins", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_school_admin_inherits_educator",
        "school_admins",
        "educators",
        ["id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint("fk_student_inherits_reader", "students", type_="foreignkey")
    op.drop_constraint("fk_student_school", "students", type_="foreignkey")
    op.drop_constraint("fk_student_class_group", "students", type_="foreignkey")
    op.create_foreign_key(
        "fk_student_school",
        "students",
        "schools",
        ["school_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_student_class_group",
        "students",
        "class_groups",
        ["class_group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_student_inherits_reader",
        "students",
        "readers",
        ["id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        "fk_wriveted_admin_inherits_user", "wriveted_admins", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_wriveted_admin_inherits_user",
        "wriveted_admins",
        "users",
        ["id"],
        ["id"],
        ondelete="CASCADE",
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        "fk_wriveted_admin_inherits_user", "wriveted_admins", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_wriveted_admin_inherits_user", "wriveted_admins", "users", ["id"], ["id"]
    )
    op.drop_constraint("fk_student_inherits_reader", "students", type_="foreignkey")
    op.drop_constraint("fk_student_class_group", "students", type_="foreignkey")
    op.drop_constraint("fk_student_school", "students", type_="foreignkey")
    op.create_foreign_key(
        "fk_student_class_group", "students", "class_groups", ["class_group_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_student_school", "students", "schools", ["school_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_student_inherits_reader", "students", "readers", ["id"], ["id"]
    )
    op.drop_constraint(
        "fk_school_admin_inherits_educator", "school_admins", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_school_admin_inherits_educator",
        "school_admins",
        "educators",
        ["id"],
        ["id"],
    )
    op.drop_constraint("fk_reader_inherits_user", "readers", type_="foreignkey")
    op.create_foreign_key("fk_reader_inherits_user", "readers", "users", ["id"], ["id"])
    op.drop_constraint(
        "fk_public_reader_inherits_reader", "public_readers", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_public_reader_inherits_reader", "public_readers", "readers", ["id"], ["id"]
    )
    op.drop_constraint("fk_parent_inherits_user", "parents", type_="foreignkey")
    op.create_foreign_key("fk_parent_inherits_user", "parents", "users", ["id"], ["id"])
    op.drop_constraint("fk_educator_inherits_user", "educators", type_="foreignkey")
    op.drop_constraint("fk_educator_school", "educators", type_="foreignkey")
    op.create_foreign_key(
        "fk_educator_inherits_user", "educators", "users", ["id"], ["id"]
    )
    op.create_foreign_key(
        "fk_educator_school", "educators", "schools", ["school_id"], ["id"]
    )
    op.drop_constraint("fk_class_groups_school", "class_groups", type_="foreignkey")
    op.create_foreign_key(
        "fk_class_groups_school",
        "class_groups",
        "schools",
        ["school_id"],
        ["wriveted_identifier"],
    )
    # ### end Alembic commands ###
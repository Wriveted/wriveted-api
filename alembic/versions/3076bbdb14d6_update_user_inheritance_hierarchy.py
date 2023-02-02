"""update user inheritance hierarchy

Revision ID: 3076bbdb14d6
Revises: cf1000e6f66b
Create Date: 2022-06-01 00:06:24.749219

"""
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "3076bbdb14d6"
down_revision = "cf1000e6f66b"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###

    # create tables, keys, and indexes
    op.create_table(
        "parents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_info", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["id"], ["users.id"], name="fk_parent_inherits_user"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "wriveted_admins",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("wriveted_admin_info", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["id"], ["users.id"], name="fk_wriveted_admin_inherits_user"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "educators",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("educator_info", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["id"], ["users.id"], name="fk_educator_inherits_user"),
        sa.ForeignKeyConstraint(
            ["school_id"], ["schools.id"], name="fk_educator_school"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_educators_school_id"), "educators", ["school_id"], unique=False
    )
    op.create_table(
        "readers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reading_preferences", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["id"], ["users.id"], name="fk_reader_inherits_user"),
        sa.ForeignKeyConstraint(["parent_id"], ["parents.id"], name="fk_reader_parent"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_readers_parent_id"), "readers", ["parent_id"], unique=False
    )
    op.create_index(op.f("ix_readers_username"), "readers", ["username"], unique=True)
    op.create_table(
        "public_readers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reader_info", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["id"], ["readers.id"], name="fk_public_reader_inherits_reader"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "school_admins",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("school_admin_info", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["id"], ["educators.id"], name="fk_school_admin_inherits_educator"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "students",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("student_info", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["id"], ["readers.id"], name="fk_student_inherits_reader"
        ),
        sa.ForeignKeyConstraint(
            ["school_id"], ["schools.id"], name="fk_student_school"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_students_school_id"), "students", ["school_id"], unique=False
    )

    # instantiate table objects to access op.bulk_insert without relying on model
    meta = sa.MetaData()
    meta.reflect(
        only=(
            "readers",
            "public_readers",
            "educators",
            "school_admins",
            "parents",
            "wriveted_admins",
        ),
        bind=op.get_bind(),
    )
    readers_table = sa.Table("readers", meta)
    public_readers_table = sa.Table("public_readers", meta)
    students_table = sa.Table("students", meta)
    educators_table = sa.Table("educators", meta)
    school_admins_table = sa.Table("school_admins", meta)
    wriveted_admins_table = sa.Table("wriveted_admins", meta)

    # ---populate the new inheritance tables with users bearing the respective types---
    conn = op.get_bind()

    # reader
    res = conn.execute(
        text("select id from users where type = 'PUBLIC' or type = 'STUDENT'")
    )
    results = res.fetchall()
    op.bulk_insert(
        readers_table, [{"id": str(r[0]), "reading_preferences": {}} for r in results]
    )

    # public reader
    res = conn.execute(text("select id from users where type = 'PUBLIC'"))
    results = res.fetchall()
    op.bulk_insert(
        public_readers_table,
        [{"id": str(r[0]), "public_reader_info": {}} for r in results],
    )

    # students
    res = conn.execute(
        text("select id, school_id_as_student from users where type = 'STUDENT'")
    )
    results = res.fetchall()
    op.bulk_insert(
        students_table,
        [
            {"id": str(r[0]), "school_id": str(r[1]), "student_info": {}}
            for r in results
        ],
    )

    # educator
    res = conn.execute(
        text(
            "select id, school_id_as_admin from users where type = 'EDUCATOR' or type = 'SCHOOL_ADMIN'"
        )
    )
    results = res.fetchall()
    op.bulk_insert(
        educators_table,
        [
            {"id": str(r[0]), "school_id": str(r[1]), "educator_info": {}}
            for r in results
        ],
    )

    # school admin
    res = conn.execute(text("select id from users where type = 'SCHOOL_ADMIN'"))
    results = res.fetchall()
    op.bulk_insert(
        school_admins_table,
        [{"id": str(r[0]), "school_admin_info": {}} for r in results],
    )

    # wriveted_admins
    res = conn.execute(text("select id from users where type = 'WRIVETED'"))
    results = res.fetchall()
    op.bulk_insert(
        wriveted_admins_table,
        [{"id": str(r[0]), "wriveted_admin_info": {}} for r in results],
    )

    # clean up schools table
    op.drop_constraint("schools_admin_id_fkey", "schools", type_="foreignkey")
    op.drop_column("schools", "admin_id")

    # clean up original users table
    op.drop_index("ix_users_school_id_as_admin", table_name="users")
    op.drop_index("ix_users_school_id_as_student", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_constraint("fk_admin_school", "users", type_="foreignkey")
    op.drop_constraint("fk_student_school", "users", type_="foreignkey")
    op.drop_column("users", "username")
    op.drop_column("users", "school_id_as_admin")
    op.drop_column("users", "school_id_as_student")


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "users",
        sa.Column(
            "school_id_as_student", sa.INTEGER(), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "school_id_as_admin", sa.INTEGER(), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        "users", sa.Column("username", sa.VARCHAR(), autoincrement=False, nullable=True)
    )
    op.create_foreign_key(
        "fk_student_school", "users", "schools", ["school_id_as_student"], ["id"]
    )
    op.create_foreign_key(
        "fk_admin_school", "users", "schools", ["school_id_as_admin"], ["id"]
    )
    op.create_index("ix_users_username", "users", ["username"], unique=False)
    op.create_index(
        "ix_users_school_id_as_student", "users", ["school_id_as_student"], unique=False
    )
    op.create_index(
        "ix_users_school_id_as_admin", "users", ["school_id_as_admin"], unique=False
    )
    op.add_column(
        "schools",
        sa.Column("admin_id", postgresql.UUID(), autoincrement=False, nullable=True),
    )
    op.create_foreign_key(
        "schools_admin_id_fkey", "schools", "users", ["admin_id"], ["id"]
    )

    op.drop_index(op.f("ix_students_school_id"), table_name="students")
    op.drop_table("students")
    op.drop_table("school_admins")
    op.drop_table("public_readers")
    op.drop_index(op.f("ix_readers_username"), table_name="readers")
    op.drop_index(op.f("ix_readers_parent_id"), table_name="readers")
    op.drop_table("readers")
    op.drop_index(op.f("ix_educators_school_id"), table_name="educators")
    op.drop_table("educators")
    op.drop_table("wriveted_admins")
    op.drop_table("parents")
    # ### end Alembic commands ###

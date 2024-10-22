"""update user enum

Revision ID: cf1000e6f66b
Revises: 2b2edef753de
Create Date: 2022-05-31 22:04:45.437888

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "cf1000e6f66b"
down_revision = "2b2edef753de"
branch_labels = None
depends_on = None


def upgrade():
    # unfortunately the cleanest way to update enums in alembic is to use raw sql

    # temporarily switch to text as we need to update rows, but new enum values cannot be accessed in this transaction
    op.execute("ALTER TABLE users ALTER COLUMN type TYPE text USING type::text")

    # remove constraint to be able to modify
    op.execute("ALTER TABLE users ALTER COLUMN type DROP DEFAULT")

    # the only toe-stepping is the renaming of library to school_admin, manually update those users
    op.execute(
        "UPDATE users SET type = 'SCHOOL_ADMIN' where type = 'LIBRARY' and school_id_as_admin is not null"
    )

    # actually, let's also set other unaccounted for accounts (lms) to public just in case
    op.execute(
        "UPDATE users SET type = 'PUBLIC' where type not in ('PUBLIC', 'STUDENT', 'WRIVETED', 'SCHOOL_ADMIN')"
    )

    # now update the underlying enum type, then switch the column back to enum
    op.execute("ALTER TYPE enum_user_account_type RENAME TO enum_user_account_type_old")
    op.execute(
        "CREATE TYPE enum_user_account_type AS ENUM('EDUCATOR', 'PARENT', 'PUBLIC', 'SCHOOL_ADMIN', 'STUDENT', 'WRIVETED')"
    )
    op.execute(
        "ALTER TABLE users ALTER COLUMN type TYPE enum_user_account_type USING type::text::enum_user_account_type"
    )
    op.execute("DROP TYPE enum_user_account_type_old")

    # return the constraint
    op.execute("ALTER TABLE users ALTER COLUMN type SET DEFAULT 'PUBLIC'")


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute("ALTER TABLE users ALTER COLUMN type TYPE text USING type::text")
    op.execute("ALTER TABLE users ALTER COLUMN type DROP DEFAULT")

    op.execute(
        "UPDATE users SET type = 'LIBRARY' where type in ('EDUCATOR', 'SCHOOL_ADMIN')"
    )
    op.execute("UPDATE users SET type = 'PUBLIC' where type = 'PARENT'")

    op.execute("ALTER TYPE enum_user_account_type RENAME TO enum_user_account_type_old")
    op.execute(
        "CREATE TYPE enum_user_account_type AS ENUM('PUBLIC', 'LMS', 'STUDENT', 'WRIVETED', 'LIBRARY')"
    )
    op.execute(
        "ALTER TABLE users ALTER COLUMN type TYPE enum_user_account_type USING type::text::enum_user_account_type"
    )
    op.execute("DROP TYPE enum_user_account_type_old")

    op.execute("ALTER TABLE users ALTER COLUMN type SET DEFAULT 'PUBLIC'")
    # ### end Alembic commands ###

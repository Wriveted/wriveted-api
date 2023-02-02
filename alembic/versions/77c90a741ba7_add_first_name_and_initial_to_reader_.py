"""Add first name and initial to reader table

Revision ID: 77c90a741ba7
Revises: 3076bbdb14d6
Create Date: 2022-06-02 15:03:17.406912

"""
import sqlalchemy as sa

# revision identifiers, used by Alembic.
from sqlalchemy import text, update

from alembic import op

revision = "77c90a741ba7"
down_revision = "3076bbdb14d6"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "readers",
        sa.Column("first_name", sa.String(), server_default="", nullable=False),
    )
    op.add_column(
        "readers",
        sa.Column("last_name_initial", sa.String(), server_default="", nullable=False),
    )
    meta = sa.MetaData()
    meta.reflect(only=("readers",), bind=op.get_bind())
    readers_table = sa.Table("readers", meta)
    conn = op.get_bind()

    res = conn.execute(
        text("select id, name from users where type = 'PUBLIC' or type = 'STUDENT'")
    )
    results = res.fetchall()
    for userid, name in results:
        conn.execute(
            update(readers_table)
            .where(readers_table.c.id == str(userid))
            .values(
                first_name=name.split()[0] if name is not None else "",
                last_name_initial=name.split()[1][0]
                if name is not None and len(name.split()) > 1
                else "",
            )
        )

    op.alter_column("readers", "first_name", server_default=None)
    op.alter_column("readers", "last_name_initial", server_default=None)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("readers", "last_name_initial")
    op.drop_column("readers", "first_name")
    # ### end Alembic commands ###

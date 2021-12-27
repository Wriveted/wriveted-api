"""Add initial root users

Revision ID: e4f0666727f3
Revises: 998f29940cbf
Create Date: 2021-12-28 11:20:41.297418

"""
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy import orm

# revision identifiers, used by Alembic.
from app.models import User

revision = 'e4f0666727f3'
down_revision = '998f29940cbf'
branch_labels = None
depends_on = None

initial_users = [
    {
        "name": "Brian",
        "email": "hardbyte@gmail.com"
    },
    {
        "name": "Meena",
        "email": "meena@wriveted.com"
    },
    {
        "name": "Caroline",
        "email": "carolinegkl@gmail.com"
    },
]


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    for data in initial_users:
        session.add(
            User(
                id=uuid4(),
                name=data['name'],
                email=data['email'],
                is_active=True,
                is_superuser=True,
            )
        )
    session.commit()

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    session.query(User).delete()
    # ### end Alembic commands ###

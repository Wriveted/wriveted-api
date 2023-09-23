"""Add reading abilities

Revision ID: 3d0364f5cfe8
Revises: b4e7bf4be9b6
Create Date: 2022-03-09 22:03:47.064036

"""
from sqlalchemy import orm

from alembic import op
from app.models import ReadingAbility

intiial_reading_abilities = [
    {"key": "SPOT", "name": "Where's Spot"},
    {"key": "CAT_HAT", "name": "The Cat in the Hat"},
    {"key": "TREEHOUSE", "name": "The 13-Storey Treehouse"},
    {"key": "CHARLIE_CHOCOLATE", "name": "Charlie and the Chocolate Factory"},
    {"key": "HARRY_POTTER", "name": "Harry Potter and the Philosopher's Stone"},
]

# revision identifiers, used by Alembic.
revision = "3d0364f5cfe8"
down_revision = "b4e7bf4be9b6"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    for data in intiial_reading_abilities:
        session.add(
            ReadingAbility(
                key=data["key"],
                name=data["name"],
            )
        )
    session.commit()
    pass


def downgrade():
    pass

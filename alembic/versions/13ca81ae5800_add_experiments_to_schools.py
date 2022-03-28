"""Add experiments to schools

Revision ID: 13ca81ae5800
Revises: ad2bcbab60ae
Create Date: 2022-03-24 13:54:33.245721

"""
from alembic import op

# revision identifiers, used by Alembic.
from sqlalchemy import orm, select, update

from app.models import School

revision = "13ca81ae5800"
down_revision = "ad2bcbab60ae"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    for school in session.execute(select(School)).scalars().all():
        if school.info is None:
            school.info = {
                "location": {
                    "suburb": None,
                    "state": "Unknown",
                    "postcode": ""
                }
            }

        school.info['experiments'] = {
            "no-jokes": False,
            "no-choice-option": True
        }
        session.add(school)

    session.commit()

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    for school in session.execute(select(School)).scalars().all():
        info = dict(school.info)
        if "experiments" in info:
            del info["experiments"]
            school.info = info
            session.add(school)

    session.commit()

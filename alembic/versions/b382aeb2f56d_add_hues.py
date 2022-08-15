"""Add Hues

Revision ID: b382aeb2f56d
Revises: 5fff4615d51a
Create Date: 2022-03-09 14:45:18.915196

"""
import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.ext.automap import automap_base

from alembic import op

Base = automap_base()


# revision identifiers, used by Alembic.
revision = "b382aeb2f56d"
down_revision = "5fff4615d51a"
branch_labels = None
depends_on = None

initial_hues = [
    {"key": "hue01_dark_suspense", "name": "Dark/Suspense"},
    {"key": "hue02_beautiful_whimsical", "name": "Beautiful/Whimsical"},
    {"key": "hue03_dark_beautiful", "name": "Dark/Beautiful"},
    {"key": "hue05_funny_comic", "name": "Funny/Comic"},
    {"key": "hue06_dark_gritty", "name": "Dark/Gritty"},
    {"key": "hue07_silly_charming", "name": "Silly/Charming"},
    {"key": "hue08_charming_inspiring", "name": "Charming/Inspiring"},
    {"key": "hue09_charming_playful", "name": "Charming/Playful"},
    {"key": "hue10_inspiring", "name": "Inspiring"},
    {"key": "hue11_realistic_hope", "name": "Realistic/Hope"},
    {"key": "hue12_funny_quirky", "name": "Funny/Quirky"},
    {"key": "hue13_straightforward", "name": "Straightforward"},
]


def upgrade():
    bind = op.get_bind()

    # Reflect the ORM models from the database at this point in time
    # Ref: https://stackoverflow.com/questions/13676744/using-the-sqlalchemy-orm-inside-an-alembic-migration-how-do-i/70985446#70985446
    Base.prepare(autoload_with=bind)

    Hue = Base.classes.hues  # Map table name to class

    session = orm.Session(bind=bind)
    for data in initial_hues:
        session.add(
            Hue(
                key=data["key"],
                name=data["name"],
            )
        )
    session.commit()
    pass


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    bind = op.get_bind()
    Base.prepare(autoload_with=bind)
    LabelSetHue = Base.classes.labelset_hue_association
    # LabelSets = Base.classes.labelsets
    Hue = Base.classes.hues

    session = orm.Session(bind=bind)
    session.query(LabelSetHue).delete()
    session.query(Hue).delete()
    # ### end Alembic commands ###

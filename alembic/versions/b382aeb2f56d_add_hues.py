"""Add Hues

Revision ID: b382aeb2f56d
Revises: 5fff4615d51a
Create Date: 2022-03-09 14:45:18.915196

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import orm
from app.models import Hue


# revision identifiers, used by Alembic.
revision = 'b382aeb2f56d'
down_revision = '5fff4615d51a'
branch_labels = None
depends_on = None

intiial_hues = [
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
    {"key": "hue13_straightforward", "name": "Straightforward"}
]

def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    
    for data in intiial_hues:
        session.add(
            Hue(
                key=data['key'],
                name=data['name'],
            )
        )
    session.commit()
    pass


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    session.query(Hue).delete()
    # ### end Alembic commands ###

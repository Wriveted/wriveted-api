from sqlalchemy import Table, Column, ForeignKey, Enum
from app.db import Base
import enum

class Ordinal(str, enum.Enum):
    PRIMARY   = "primary"
    SECONDARY = "secondary"
    TERTIARY  = "tertiary"

hue_work_association_table = Table(
    'hue_work_association', Base.metadata,
    Column('work_id',
           ForeignKey('works.id', name="fk_hue_works_association_work_id"),
           primary_key=True),
    Column('hue_id',
           ForeignKey('hues.id', name="fk_hue_works_association_hue_id"),
           primary_key=True),
    Column('ordinal', 
           Enum(Ordinal), 
           primary_key=True)
)

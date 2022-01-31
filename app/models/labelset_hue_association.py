from sqlalchemy import Table, Column, ForeignKey, Enum
from app.db import Base
import enum

class Ordinal(str, enum.Enum):
    PRIMARY   = "primary"
    SECONDARY = "secondary"
    TERTIARY  = "tertiary"
    

labelset_hue_association_table = Table(
    'labelset_hue_association', Base.metadata,
    Column('labelset_id',
           ForeignKey('labelsets.id', name="fk_labelset_hue_association_labelset_id"),
           primary_key=True),
    Column('hue_id',
           ForeignKey('hues.id', name="fk_labelset_hue_association_hue_id"),
           primary_key=True),
    Column('ordinal', 
           Enum(Ordinal), 
           primary_key=True)
)

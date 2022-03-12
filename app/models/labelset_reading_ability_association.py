from sqlalchemy import Table, Column, ForeignKey
from app.db import Base

labelset_reading_ability_association_table = Table(
    "labelset_reading_ability_association",
    Base.metadata,
    Column(
        "labelset_id",
        ForeignKey(
            "labelsets.id", name="fk_labelset_reading_ability_association_labelset_id"
        ),
        primary_key=True,
    ),
    Column(
        "reading_ability_id",
        ForeignKey(
            "reading_abilities.id",
            name="fk_labelset_reading_ability_association_reading_ability_id",
        ),
        primary_key=True,
    ),
)

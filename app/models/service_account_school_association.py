from sqlalchemy import Table, Column, ForeignKey

from app.db import Base

service_account_school_association_table = Table(
    "service_account_school_association",
    Base.metadata,
    Column(
        "service_account_id",
        ForeignKey(
            "service_accounts.id",
            name="fk_service_account_school_association_service_account",
        ),
        primary_key=True,
    ),
    Column(
        "school_id",
        ForeignKey("schools.id", name="fk_service_account_school_association_school"),
        primary_key=True,
    ),
)

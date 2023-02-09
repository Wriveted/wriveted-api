import uuid
from typing import Annotated

from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column

user_fk = Annotated[uuid.UUID, mapped_column(ForeignKey("users.id"))]
intpk = Annotated[int, mapped_column(primary_key=True)]

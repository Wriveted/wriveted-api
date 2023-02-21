from typing import Annotated

from sqlalchemy.orm import mapped_column

# This ran into trouble creating duplicated foreign keys across the
# polymorphic user tables. Use with care!
# user_fk = Annotated[uuid.UUID, mapped_column(ForeignKey("users.id"))]

intpk = Annotated[int, mapped_column(primary_key=True)]

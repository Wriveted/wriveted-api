from typing import Any, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud import CRUDBase
from app.models import Hue
from app.schemas.hue import HueCreateIn

class CRUDHue(CRUDBase[Hue, HueCreateIn, Any]):
    def get_by_key(self, db: Session, key: str) -> Optional[Hue]:
        return db.execute(select(Hue).where(Hue.key == key)).scalar_one_or_none()

hue = CRUDHue(Hue)
from typing import Any

from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.crud import CRUDBase
from app.models import ServiceAccount

from app.schemas.service_account import ServiceAccountCreateIn

logger = get_logger()


class CRUDServiceAccount(CRUDBase[ServiceAccount, ServiceAccountCreateIn, Any]):
    def create(self, db: Session, *, obj_in: ServiceAccountCreateIn, commit=True) -> ServiceAccount:
        # Remove the schools, create the service account, then link to the schools
        schools = []
        if obj_in.schools is not None:
            # Copy the list of schools to link to
            schools = list(obj_in.schools)
            obj_in.schools = []

        svc_account = super().create(db=db, obj_in=obj_in, commit=False)
        for school in schools:
            svc_account.schools.append(crud.school.get_by_official_id_or_404(
                db=db,
                country_code=school.country_code,
                official_id=school.official_identifier
            ))

        if commit:
            db.commit()
            db.refresh(svc_account)

        return svc_account


service_account = CRUDServiceAccount(ServiceAccount)

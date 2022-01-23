from typing import Any, Dict, List, Union

from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.crud import CRUDBase
from app.models import ServiceAccount
from app.schemas.school import SchoolIdentity

from app.schemas.service_account import ServiceAccountCreateIn, ServiceAccountUpdateIn

logger = get_logger()


class CRUDServiceAccount(CRUDBase[ServiceAccount, ServiceAccountCreateIn, ServiceAccountUpdateIn]):

    def create(self, db: Session, *, obj_in: ServiceAccountCreateIn, commit=True) -> ServiceAccount:
        # Because a ServiceAccount ORM object has a `schools` attribute, our default
        # CRUD's create method would try to set it using the Optional[List[SchoolIdentity]].
        # Instead we remove the `schools` from the input object, create the service account,
        # then link to the schools.
        schools = []
        if obj_in.schools is not None:
            # Copy the list of schools to link to
            schools = list(obj_in.schools)

        obj_in.schools = []

        svc_account = super().create(db=db, obj_in=obj_in, commit=False)
        self.add_access_to_schools(db, svc_account, schools)

        if commit:
            db.commit()
            db.refresh(svc_account)

        return svc_account

    def set_access_to_schools(self, db, svc_account: ServiceAccount, schools: List[SchoolIdentity]):
        # Replace the service account's current associated schools with the provided list.
        svc_account.schools = []
        return self.add_access_to_schools(db, svc_account, schools)

    def add_access_to_schools(self, db, svc_account: ServiceAccount, schools: List[SchoolIdentity]):
        for school in schools:
            svc_account.schools.append(crud.school.get_by_official_id_or_404(
                db=db,
                country_code=school.country_code,
                official_id=school.official_identifier
            ))

    def update(self, db: Session, *, db_obj: ServiceAccount,
               obj_in: Union[ServiceAccountUpdateIn, Dict[str, Any]]) -> ServiceAccount:
        svc_account = super().update(db=db, db_obj=db_obj, obj_in=obj_in)
        if obj_in.schools is not None:
            self.set_access_to_schools(db=db, svc_account=svc_account, schools=obj_in.schools)
        return svc_account


service_account = CRUDServiceAccount(ServiceAccount)

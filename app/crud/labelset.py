from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from structlog import get_logger
from app import crud
from app.crud import CRUDBase
from app.models.hue import Hue
from app.models.labelset import LabelSet
from app.models.work import Work
from app.schemas.labelset import LabelSetCreateIn
from app.models import LabelSetHue

ORIGIN_WEIGHTS = {
    "HUMAN":             4,
    "CLUSTER_RELEVANCE": 3,
    "CLUSTER_ZAINAB":    2,
    "PREDICTED_NIELSEN": 1
}

logger = get_logger()

class CRUDLabelset(CRUDBase[LabelSet, LabelSetCreateIn, Any]):
    def get_or_create(
        self, db: Session, work: Work, commit=True
    ) -> LabelSet:

        labelset = work.labelset
        if not labelset:
            labelset = LabelSet(
                work=work
            )
            db.add(labelset)
            if commit :
                db.commit()
            
        return labelset


    def patch(
        self, db: Session, labelset: LabelSet, data: LabelSetCreateIn, commit=True
    ) -> LabelSet:
        """Fill a LabelSet with data, replacing existing if the origin of new data holds more authority"""

        updated = False

        if data.hue_origin and (data.hue_primary_key or data.hue_secondary_key or data.hue_tertiary_key):
            # we only want to patch the hues if there were previously none, or if the origin of any new ones holds more authority
            if labelset.hue_origin is None or \
                ORIGIN_WEIGHTS[labelset.hue_origin] < ORIGIN_WEIGHTS[data.hue_origin.name]:
                    labelset_hues: list[LabelSetHue] = db.execute(select(LabelSetHue)\
                        .where(LabelSetHue.labelset_id == labelset.id)).scalars().all()

                    # if primary/secondary/tertiary hues have been specified, replace them in the association table 
                    # (provided a hue with that key exists) otherwise, create associations
                    if data.hue_primary_key:
                        hue: Hue = crud.hue.get_by_key(data.hue_primary_key)
                        if hue:
                            primary = next((lsh for lsh in labelset_hues if lsh.ordinal == "PRIMARY"), None)
                            if primary:
                                primary.hue_id = hue.id
                            else:
                                db.add(LabelSetHue(labelset_id=labelset.id, hue_id=hue.id, ordinal="PRIMARY"))

                    if data.hue_secondary_key:
                        hue: Hue = crud.hue.get_by_key(data.hue_secondary_key)
                        if hue:
                            secondary = next((lsh for lsh in labelset_hues if lsh.ordinal == "SECONDARY"), None)
                            if secondary:
                                secondary.hue_id = hue.id
                            else:
                                db.add(LabelSetHue(labelset_id=labelset.id, hue_id=hue.id, ordinal="SECONDARY"))

                    if data.hue_tertiary_key:
                        hue: Hue = crud.hue.get_by_key(data.hue_tertiary_key)
                        if hue:
                            tertiary = next((lsh for lsh in labelset_hues if lsh.ordinal == "TERTIARY"), None)
                            if tertiary:
                                tertiary.hue_id = hue.id
                            else:
                                db.add(LabelSetHue(labelset_id=labelset.id, hue_id=hue.id, ordinal="TERTIARY"))

                    labelset.hue_origin = data.hue_origin
                    updated = True
        
        # same idea with min/max age, re: authority
        if data.age_origin and (data.min_age or data.max_age):
            if labelset.age_origin is None or \
                ORIGIN_WEIGHTS[labelset.age_origin] < ORIGIN_WEIGHTS[data.age_origin.name]:
                    if data.min_age:
                        labelset.min_age = data.min_age

                    if data.max_age:
                        labelset.max_age = data.max_age

                    labelset.age_origin = data.age_origin 
                    updated = True                   
        
        # same with reading ability
        if data.reading_ability_origin and data.reading_ability:
            if labelset.reading_ability_origin is None or \
                ORIGIN_WEIGHTS[labelset.reading_ability_origin] < ORIGIN_WEIGHTS[data.reading_ability_origin.name]:
                    labelset.reading_ability = data.reading_ability
                    labelset.reading_ability_origin = data.reading_ability_origin
                    updated = True

        # "recommendability" can also be overridden by authority
        if data.recommend_status_origin and data.recommend_status:
            if labelset.recommend_status_origin is None or \
                ORIGIN_WEIGHTS[labelset.recommend_status_origin] < ORIGIN_WEIGHTS[data.recommend_status_origin.name]:
                    labelset.recommend_status = data.recommend_status
                    labelset.recommend_status_origin = data.recommend_status_origin
                    updated = True

        # with genres just merge the lists (relying on __eq__ and __hash__ to remove duplicates)
        if(data.genres not in labelset.genres):
            labelset.genres = list(set(labelset.genres + data.genres))
            updated = True

        if not data.info.items() <= labelset.info.items():
            labelset.info = data.info
            updated = True

        # TODO: implement a changelog for Labelsets instead of just overwriting everything
        if updated:
            if data.labelled_by_sa_id:
                labelset.labelled_by_sa_id = data.labelled_by_sa_id
            if data.labelled_by_user_id:
                labelset.labelled_by_user_id = data.labelled_by_user_id
        
        labelset.checked = data.checked

        if commit:
            db.commit()
            db.refresh(labelset)
        return labelset
        

labelset = CRUDLabelset(LabelSet)
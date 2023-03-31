from typing import Any, Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session
from structlog import get_logger

from app.crud import CRUDBase
from app.crud.base import deep_merge_dicts
from app.models import LabelSetHue
from app.models.hue import Hue
from app.models.labelset import LabelSet, RecommendStatus
from app.models.labelset_hue_association import Ordinal
from app.models.reading_ability import ReadingAbility
from app.models.work import Work
from app.schemas.labelset import LabelSetCreateIn

ORIGIN_WEIGHTS = {
    "HUMAN": 5,
    "GPT4": 4,
    "CLUSTER_RELEVANCE": 3,
    "CLUSTER_ZAINAB": 2,
    "NIELSEN_CBMC": 1.5,
    "NIELSEN_BIC": 1.4,
    "NIELSEN_THEMA": 1.3,
    "NIELSEN_IA": 1.2,
    "NIELSEN_RA": 1.1,
    "PREDICTED_NIELSEN": 1,
    "OTHER": 0,
}

logger = get_logger()


class CRUDLabelset(CRUDBase[LabelSet, LabelSetCreateIn, Any]):
    def get_hue_by_key(self, db: Session, key: str) -> Optional[Hue]:
        return db.execute(select(Hue).where(Hue.key == key)).scalar_one_or_none()

    def get_reading_ability_by_key(
        self, db: Session, key: str
    ) -> Optional[ReadingAbility]:
        return db.execute(
            select(ReadingAbility).where(ReadingAbility.key == key)
        ).scalar_one_or_none()

    def get_labelset_hues_by_labelset_id(self, db: Session, id: str) -> list[LabelSet]:
        return (
            db.execute(select(LabelSetHue).where(LabelSetHue.labelset_id == id))
            .scalars()
            .all()
        )

    def get_or_create(self, db: Session, work: Work, commit=True) -> LabelSet:

        labelset = work.labelset

        if not labelset:
            labelset = LabelSet(work=work)
            db.add(labelset)
            logger.info("Creating new labelset", labelset=labelset, work=work)
            if commit:
                db.commit()

        db.flush()
        return labelset

    def patch(
        self, db: Session, labelset: LabelSet, data: LabelSetCreateIn, commit=True
    ) -> LabelSet:
        """Fill a LabelSet with data, replacing existing if the origin of new data holds more authority"""

        updated = False

        # HUES
        if data.hue_origin and (
            not labelset.hue_origin
            or ORIGIN_WEIGHTS[labelset.hue_origin]
            <= ORIGIN_WEIGHTS[data.hue_origin.name]
        ):
            new_hues = {
                data.hue_primary_key,
                data.hue_secondary_key,
                data.hue_tertiary_key,
            }
            old_hues = {hue.key for hue in labelset.hues}

            # only update if set of new hues is different (not worried about ordinals)
            if new_hues != old_hues:
                # clear out old hues, simpler than messing with ordinals
                db.query(LabelSetHue).filter_by(labelset_id=labelset.id).delete()

                for hue_key in new_hues:
                    if hue := self.get_hue_by_key(db, hue_key):
                        ordinal = (
                            Ordinal.PRIMARY
                            if hue_key == data.hue_primary_key
                            else (
                                Ordinal.SECONDARY
                                if hue_key == data.hue_secondary_key
                                else Ordinal.TERTIARY
                            )
                        )
                        db.add(
                            LabelSetHue(
                                labelset_id=labelset.id, hue_id=hue.id, ordinal=ordinal
                            )
                        )

            # a higher authority may provide identical info, but we still want to update the origin
            labelset.hue_origin = data.hue_origin if new_hues else None
            updated = True

        # AGE
        if data.age_origin:
            if (
                labelset.age_origin is None
                or ORIGIN_WEIGHTS[labelset.age_origin]
                <= ORIGIN_WEIGHTS[data.age_origin.name]
            ):
                if data.min_age is not None:
                    labelset.min_age = data.min_age
                if data.max_age is not None:
                    labelset.max_age = data.max_age
                # doesn't make sense to remove only one of min/max age
                if data.min_age is None and data.max_age is None:
                    labelset.min_age = None
                    labelset.max_age = None
                labelset.age_origin = data.age_origin
                updated = True

        # READING ABILITY
        if data.reading_ability_origin and data.reading_ability_keys:
            if (
                labelset.reading_ability_origin is None
                or ORIGIN_WEIGHTS[labelset.reading_ability_origin]
                <= ORIGIN_WEIGHTS[data.reading_ability_origin.name]
            ):
                reading_abilities = [
                    self.get_reading_ability_by_key(db, key)
                    for key in data.reading_ability_keys
                ]
                if reading_abilities:
                    labelset.reading_abilities = reading_abilities
                    labelset.reading_ability_origin = data.reading_ability_origin
                    updated = True

        # RECOMMEND STATUS
        if (
            data.recommend_status != RecommendStatus.BAD_CONTROVERSIAL
            and data.recommend_status_origin
            and data.recommend_status
        ):
            if (
                labelset.recommend_status_origin is None
                or ORIGIN_WEIGHTS[labelset.recommend_status_origin]
                <= ORIGIN_WEIGHTS[data.recommend_status_origin.name]
            ):
                labelset.recommend_status = data.recommend_status
                labelset.recommend_status_origin = data.recommend_status_origin
                updated = True

        # GENRES
        if data.info and data.info["genres"]:
            try:
                if not labelset.info:
                    labelset.info = {}
                labelset.info["genres"] = data.info["genres"]
            except Exception as e:
                logger.warning("Some error was ignored", exc_info=e)
                pass

        # SUMMARY
        if data.summary_origin and data.huey_summary:
            if (
                labelset.summary_origin is None
                or ORIGIN_WEIGHTS[labelset.summary_origin]
                <= ORIGIN_WEIGHTS[data.summary_origin.name]
            ):
                labelset.huey_summary = data.huey_summary
                labelset.summary_origin = data.summary_origin
                updated = True

        # INFO
        if data.info:
            if not labelset.info:
                labelset.info = data.info.copy()
                updated = True
            elif data.info.items() >= labelset.info.items():
                # merge data.info into labelset.info
                deep_merge_dicts(labelset.info, data.info)
                updated = True
                # remove keys in labelset.info that are not in data.info
                for key in labelset.info.keys() - data.info.keys():
                    labelset.info[key] = None

        if updated:
            if data.labelled_by_sa_id:
                labelset.labelled_by_sa_id = data.labelled_by_sa_id
            if data.labelled_by_user_id:
                labelset.labelled_by_user_id = data.labelled_by_user_id

        if data.checked is not None:
            labelset.checked = data.checked

        if commit:
            db.commit()
            db.refresh(labelset)
        return labelset


labelset = CRUDLabelset(LabelSet)

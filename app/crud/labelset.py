from typing import Any, Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session
from structlog import get_logger

from app.crud import CRUDBase
from app.models import LabelSetHue
from app.models.hue import Hue
from app.models.labelset import LabelSet
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

    def create_or_update_labelset_hue(
        self, db: Session, labelset_id: str, hue_id: str, ordinal: Ordinal
    ):
        lsh = select(LabelSetHue).where(
            and_(
                LabelSetHue.labelset_id == labelset_id,
                LabelSetHue.hue_id == hue_id,
                LabelSetHue.ordinal == ordinal,
            )
        )
        existing = db.execute(lsh).scalar_one_or_none()
        if not existing:
            db.add(
                LabelSetHue(
                    labelset_id=labelset_id,
                    hue_id=hue_id,
                    ordinal=ordinal,
                )
            )

    def patch(
        self, db: Session, labelset: LabelSet, data: LabelSetCreateIn, commit=True
    ) -> LabelSet:
        """Fill a LabelSet with data, replacing existing if the origin of new data holds more authority"""

        updated = False

        if data.hue_origin and (
            data.hue_primary_key or data.hue_secondary_key or data.hue_tertiary_key
        ):
            # we only want to patch the hues if there were previously none, or if the origin of any
            # new ones holds at least as much authority
            if (
                labelset.hue_origin is None
                or ORIGIN_WEIGHTS[labelset.hue_origin]
                <= ORIGIN_WEIGHTS[data.hue_origin.name]
            ):
                # get any hues currently assigned to this labelset, including ordinal
                labelset_hues: list[
                    LabelSetHue
                ] = self.get_labelset_hues_by_labelset_id(db, labelset.id)

                # if primary/secondary/tertiary hues have been specified, replace them in the association table
                # (provided a hue with that key exists) otherwise, create associations
                if data.hue_primary_key:
                    hue: Hue = self.get_hue_by_key(db, data.hue_primary_key)
                    if hue:
                        primary = next(
                            (lsh for lsh in labelset_hues if lsh.ordinal == "PRIMARY"),
                            None,
                        )
                        if primary:
                            primary.hue_id = hue.id
                        else:
                            self.create_or_update_labelset_hue(
                                db, labelset.id, hue.id, Ordinal.PRIMARY
                            )

                if data.hue_secondary_key:
                    hue: Hue = self.get_hue_by_key(db, data.hue_secondary_key)
                    if hue:
                        secondary = next(
                            (
                                lsh
                                for lsh in labelset_hues
                                if lsh.ordinal == "SECONDARY"
                            ),
                            None,
                        )
                        if secondary:
                            secondary.hue_id = hue.id
                        else:
                            self.create_or_update_labelset_hue(
                                db, labelset.id, hue.id, Ordinal.SECONDARY
                            )

                if data.hue_tertiary_key:
                    hue: Hue = self.get_hue_by_key(db, data.hue_tertiary_key)
                    if hue:
                        tertiary = next(
                            (lsh for lsh in labelset_hues if lsh.ordinal == "TERTIARY"),
                            None,
                        )
                        if tertiary:
                            tertiary.hue_id = hue.id
                        else:
                            self.create_or_update_labelset_hue(
                                db, labelset.id, hue.id, Ordinal.TERTIARY
                            )

                labelset.hue_origin = data.hue_origin
                updated = True

        # same idea with min/max age, re: authority
        if data.age_origin and (data.min_age or data.max_age):
            if (
                labelset.age_origin is None
                or ORIGIN_WEIGHTS[labelset.age_origin]
                <= ORIGIN_WEIGHTS[data.age_origin.name]
            ):
                if data.min_age:
                    labelset.min_age = data.min_age
                if data.max_age:
                    labelset.max_age = data.max_age
                labelset.age_origin = data.age_origin
                updated = True

        # same with reading ability
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

        # "recommendability" can also be overridden by authority
        if data.recommend_status_origin and data.recommend_status:
            if (
                labelset.recommend_status_origin is None
                or ORIGIN_WEIGHTS[labelset.recommend_status_origin]
                <= ORIGIN_WEIGHTS[data.recommend_status_origin.name]
            ):
                labelset.recommend_status = data.recommend_status
                labelset.recommend_status_origin = data.recommend_status_origin
                updated = True

        # with genres just add the dict to the info blob
        if data.info and data.info["genres"]:
            try:
                if not data.info:
                    data.info = {}
                labelset.info["genres"] = data.info["genres"]
            except Exception as e:
                logger.warning("Some error was ignored", exc_info=e)
                pass

        # now summary
        if data.summary_origin and data.huey_summary:
            if (
                labelset.summary_origin is None
                or ORIGIN_WEIGHTS[labelset.summary_origin]
                <= ORIGIN_WEIGHTS[data.summary_origin.name]
            ):
                labelset.huey_summary = data.huey_summary
                labelset.summary_origin = data.summary_origin
                updated = True

        # if the new Info object provides anything new, add the changes
        if data.info and (
            not labelset.info or (data.info.items() >= labelset.info.items())
        ):
            labelset.info = data.info
            updated = True

        # TODO: implement a changelog for Labelsets instead of just overwriting everything
        if updated:
            if data.labelled_by_sa_id:
                labelset.labelled_by_sa_id = data.labelled_by_sa_id
            if data.labelled_by_user_id:
                labelset.labelled_by_user_id = data.labelled_by_user_id

        labelset.checked = not not data.checked

        if commit:
            db.commit()
            db.refresh(labelset)
        return labelset


labelset = CRUDLabelset(LabelSet)

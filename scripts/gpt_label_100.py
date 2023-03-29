from sqlalchemy import or_
from sqlalchemy.orm import Session
from structlog import get_logger
from app import crud

from app.config import get_settings
from app.crud.base import compare_dicts
from app.db.session import database_connection
from app.models import Edition
from app.models.labelset import LabelOrigin, LabelSet
from app.models.work import Work
from app.schemas.labelset import LabelSetCreateIn
from app.services.gpt import extract_labels

settings = get_settings()
logger = get_logger()

engine, SessionLocal = database_connection(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
)


def work_to_gpt_labelset_update(work: Work):
    gpt_data = extract_labels(work, retries=2)

    output = gpt_data.output

    labelset_data = {}

    # reading abilities
    labelset_data["reading_ability_keys"] = output.reading_ability
    labelset_data["reading_ability_origin"] = LabelOrigin.GPT4

    # hues
    if output.hues:
        labelset_data["hue_primary_key"] = output.hues[0]
    if len(output.hues) > 1:
        labelset_data["hue_secondary_key"] = output.hues[1]
    if len(output.hues) > 2:
        labelset_data["hue_tertiary_key"] = output.hues[2]
    labelset_data["hue_origin"] = LabelOrigin.GPT4

    # summary
    labelset_data["huey_summary"] = output.short_summary
    labelset_data["summary_origin"] = LabelOrigin.GPT4

    # other
    labelset_info = {}
    labelset_info["long_summary"] = output.long_summary
    labelset_info["genres"] = output.genres
    labelset_info["styles"] = output.styles
    labelset_info["characters"] = output.characters
    labelset_info["hue_map"] = output.hue_map
    labelset_info["series"] = output.series
    labelset_info["series_number"] = output.series_number
    labelset_info["gender"] = output.gender
    labelset_info["awards"] = output.awards
    labelset_info["notes"] = output.notes
    labelset_info["label_confidence"] = output.confidence

    labelset_data["info"] = labelset_info

    # mark as needing to be checked
    labelset_data["checked"] = None

    labelset_data["recommend_status"] = output.recommend_status
    labelset_data["recommend_status_origin"] = LabelOrigin.GPT4

    labelset_create = LabelSetCreateIn(**labelset_data)
    return labelset_create


def label_and_update_work(work: Work, session):
    labelset_update = work_to_gpt_labelset_update(work)

    labelset = crud.labelset.get_or_create(session, work, False)
    old_labelset_data = labelset.get_label_dict(session)
    new_labelset = crud.labelset.patch(session, labelset, labelset_update, True)
    new_labelset_data = labelset.get_label_dict(session)
    crud.event.create(
        session,
        title=f"Label edited",
        description=f"GPT Script labelled {work.title}",
        info={
            "changes": compare_dicts(old_labelset_data, new_labelset_data),
            "work_id": work.id,
            "labelset_id": labelset.id,
        },
    )

    new_labelset.checked = None
    session.commit()

    logger.info(f"Updated labelset for {work.title}")


with Session(engine) as session:
    # select Works where:
    # their associated labelset has min and max age,
    # their associated lableset is missing reading abilities and/or hues
    # at least one edition has a cover image,
    # at least one edition has a publication date after 2015,
    works = (
        session.query(Work)
        .join(Work.labelset)
        .filter(
            LabelSet.min_age.isnot(None),
            LabelSet.max_age.isnot(None),
            or_(
                ~LabelSet.reading_abilities.any(),
                ~LabelSet.hues.any(),
            ),
            Work.editions.any(Edition.cover_url.isnot(None)),
            Work.editions.any(Edition.date_published > 20150000),
        )
        .limit(200)
        .all()
    )

    print(f"Found {len(works)} works to label")

    count = 0
    for work in works:
        if count >= 100:
            break
        try:
            label_and_update_work(work, session)
            count += 1
        except ValueError:
            logger.warning(f"Failed to label {work.title}. Skipping...")
            continue

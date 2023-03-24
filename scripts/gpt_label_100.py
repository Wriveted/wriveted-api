from rich import print
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app import crud
from app.api.works import update_work

from app.config import get_settings
from app.db.session import database_connection
from app.models import Edition
from app.models.labelset import LabelOrigin, LabelSet
from app.models.work import Work
from app.schemas.labelset import LabelSetCreateIn
from app.schemas.work import WorkUpdateIn
from app.services.gpt import extract_labels

settings = get_settings()

engine, SessionLocal = database_connection(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
)


def work_to_gpt_labelset_update(work: Work):
    try:
        gpt_data = extract_labels(work, retries=2)
    except ValueError as e:
        print(e)
        exit()

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
    labelset_info["awards"] = output.awards
    labelset_info["notes"] = output.notes

    labelset_data["info"] = labelset_info

    # mark as needing to be checked
    labelset_data["checked"] = False

    labelset_create = LabelSetCreateIn(**labelset_data)
    return labelset_create


def label_and_update_work(work: Work, session):
    labelset_update = work_to_gpt_labelset_update(work)

    labelset = crud.labelset.get_or_create(session, work, False)
    old_labelset_data = dict(labelset.__dict__)

    new_labelset = crud.labelset.patch(session, labelset, labelset_update, True)
    new_labelset_data = dict(new_labelset.__dict__)

    diff = {}
    for key in old_labelset_data:
        if key.startswith("_"):  # Ignore private attributes
            continue
        if old_labelset_data[key] != new_labelset_data[key]:
            diff[key] = new_labelset_data[key]

    print(f"Updated labelset for {work.title}. Changes:", diff)


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
        .limit(50)
        .all()
    )

    print(f"Found {len(works)} works to label")

    for work in works:
        label_and_update_work(work, session)

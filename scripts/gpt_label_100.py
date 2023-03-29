from sqlalchemy import or_
from sqlalchemy.orm import Session
from structlog import get_logger

from app.config import get_settings
from app.db.session import database_connection
from app.models import Edition
from app.models.labelset import LabelSet
from app.models.work import Work
from app.services.gpt import label_and_update_work

settings = get_settings()
logger = get_logger()

engine, SessionLocal = database_connection(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
)

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

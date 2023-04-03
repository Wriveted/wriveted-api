import asyncio
from sqlalchemy import or_
from sqlalchemy.orm import Session
from structlog import get_logger

from app.config import get_settings
from app.db.session import database_connection
from app.models import Edition
from app.models.labelset import LabelSet
from app.models.work import Work
from app.services.events import create_event
from app.services.gpt import label_and_update_work

settings = get_settings()
logger = get_logger()

engine, SessionLocal = database_connection(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
)


async def label():
    while True:
        with Session(engine) as session:
            # select a Work where:
            # its associated labelset has min and max age,
            # its associated lableset is missing reading abilities and/or hues
            # at least one edition has a cover image,
            # order by date published descending
            work = (
                session.query(Work)
                .join(Work.labelset)
                .join(Edition)
                .filter(
                    LabelSet.min_age.isnot(None),
                    LabelSet.max_age.isnot(None),
                    or_(
                        ~LabelSet.reading_abilities.any(),
                        ~LabelSet.hues.any(),
                    ),
                    Work.editions.any(Edition.cover_url.isnot(None)),
                )
                .order_by(Edition.date_published.desc())
                .limit(1)
                .one_or_none()
            )

            try:
                await label_and_update_work(work, session)
            except ValueError as e:
                create_event(
                    session,
                    "GPT Labeling Failed",
                    f"Failed to label {work.title}.",
                    {"work_id": work.id, "error": str(e)},
                )
                logger.warning(f"Failed to label {work.title}. Skipping...")
                continue


async def main():
    tasks = []
    for _ in range(3):
        tasks.append(asyncio.create_task(label()))
        await asyncio.sleep(20)
    await asyncio.gather(*tasks)


asyncio.run(main())

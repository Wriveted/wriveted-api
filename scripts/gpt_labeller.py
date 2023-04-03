import asyncio
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import contains_eager
from sqlalchemy.orm import Session
from structlog import get_logger

from app.config import get_settings
from app.crud import event as crud_event
from app.db.session import database_connection
from app.models import Edition
from app.models.collection import Collection
from app.models.collection_item import CollectionItem
from app.models.labelset import LabelSet
from app.models.work import Work

# from app.services.events import create_event
from app.services.gpt import label_and_update_work

settings = get_settings()
logger = get_logger()

engine, SessionLocal = database_connection(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
)

school_ids = [
    "1e698bfa-dcc6-4993-9fce-b4d35c427c47",
    "4b4eb2db-9442-4c6a-bfc4-467c4df439ba",
    "72603041-d2f9-4ae6-8e4c-e2f85d9d101f",
    "7ad69d31-e603-420d-b81d-17a09106718b",
    "df6dc32c-a03d-456a-8ca2-d386ec4a00e2",
    "9f798813-865f-4129-87ca-9ef170015325",
    "09d37f3c-b494-407b-8b2c-572c7985a59f",
    "be63175e-b81e-4f2b-a853-5d9ed0cf0e57",
    "851b23be-7b17-4b59-bd59-2f3765ad753c",
    "b8a80b9e-cd71-409e-8a70-76f758e1d157",
    "aa1d9753-3975-4912-b0eb-62ad64ad7e1a",
    "416f3908-bd7f-42c8-ac2c-58eb26339d48",
    "70759ce9-f139-4bab-b396-16835d0d92a6",
    "9733579e-452d-4a2b-b677-dece8f87ee21",
    "334929c2-c031-4a8f-8da9-03f749ab6b3e",
    "fb0919d9-4510-46a1-87e9-1ab2c27c91cf",
    "b384ffd1-36ad-4fb9-9dfd-4277453ff903",
    "2546a8c8-0015-4059-98bc-dccfb3c9cfb0",
    "cbe0280b-5350-4a32-b524-ef13043d1db8",
    "99928227-466f-4d33-9a1e-ce37eaa033d6",
]


async def label():
    while True:
        with Session(engine) as session:
            # select a Work where:
            # its associated labelset has min and max age,
            # its associated lableset is missing reading abilities and/or hues
            # at least one edition has a cover image,
            # the book appears in a collection associated with a top school,
            # order by date published descending
            work = (
                session.query(Work)
                .join(Work.labelset)
                .join(Edition)
                .join(
                    CollectionItem,
                    and_(
                        Edition.isbn == CollectionItem.edition_isbn,
                        CollectionItem.collection_id.in_(
                            select(Collection.id).where(
                                Collection.school_id.in_(school_ids)
                            )
                        ),
                    ),
                    isouter=True,
                )
                .join(Collection)
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
                .options(
                    contains_eager(Work.editions).contains_eager(Edition.collections)
                )
                .limit(1)
                .one_or_none()
            )

            try:
                await label_and_update_work(work, session)
            except ValueError as e:
                crud_event.create(
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

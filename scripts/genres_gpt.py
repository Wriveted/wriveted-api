from typing import List

from rich import print
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import database_connection
from app.models import Edition
from app.services.gpt import extract_labels

settings = get_settings()

engine, SessionLocal = database_connection(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
)

with Session(engine) as session:
    # sample recently liked editions
    # recently_liked_isbns = session.scalars(text("""
    # with recently_liked_isbns as (
    # SELECT
    #     value->>'isbn' as "isbn",
    #     value->>'title' as "Title"
    # FROM events
    # cross join jsonb_array_elements(events.info::jsonb->'reviews')
    # WHERE events.title = 'Huey: Books all reviewed' and value->>'liked' = 'true'
    # )
    #
    # select isbn from recently_liked_isbns where length(isbn) > 1 limit 50;
    # """)).all()

    recently_liked_isbns = [
        "9780571191475",
        "9780001831803",
        # "9781760150426",
        # "9780141354828",
        # "9780143303831",
        # "9780064407663",
        # "9781925163131",
        # "9780340999073",
        # "9780141359786",
        "9781742837581",
        "9781921564925",
        "9781743628638",
        "9781760525880",
        "9781760990718",
        "9781760877644",
        "9781922330963",
    ]
    editions: List[Edition] = session.scalars(
        select(Edition).where(Edition.isbn.in_(recently_liked_isbns))
    ).all()

    total_tokens = 0

    for e in editions[:2]:
        work = e.work
        print(work)

        result = extract_labels(work)

        print(result["output"])
        usage = result["usage"]

        # total_tokens += usage['tokens']

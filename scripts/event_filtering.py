# Ensure your environment variables are set such that this script can connect
# directly to the database. E.g. there are different postgres passwords if running
# via docker-compose versus a Cloud SQL database.
import logging
import os

from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.config import get_settings

logging.basicConfig()
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)


os.environ["POSTGRESQL_SERVER"] = "localhost/"
# os.environ['POSTGRESQL_PASSWORD'] = ''
os.environ["SECRET_KEY"] = ""
# Note we have to set at least the above environment variables before importing our application code

from app import models
from app.db.session import database_connection

# with SessionManager(get_session_maker()) as session:
settings = get_settings()
engine, SessionLocal = database_connection(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
)
with Session(engine) as session:
    # events = crud.event.get_all_with_optional_filters(db=session, limit=10)
    jsonpath_query = '($.reading_logged.emoji == "🤪")'
    # malicous query attempt...
    # jsonpath_query = "true'); delete from users where email='brian.thorne.nz@gmail.com'; commit;--"
    # jsonpath_query = "wrong"
    query = (
        select(models.Event)
        .where(models.Event.title == "Reader timeline event: Reading logged")
        .where(
            func.jsonb_path_match(cast(models.Event.info, JSONB), jsonpath_query).is_(
                True
            )
        )
        # .where(text(f"jsonb_path_match(info::jsonb, '{jsonpath_query}'::jsonpath)::boolean"))
        .limit(10)
    )
    thing = session.query(models.Event).one()

    stmt = select(models.Event, models.User).join_from(models.Event, models.User)
    res = session.execute(stmt)

    # (variable) rows: List[Row[Tuple[int, str]]]
    rows = q1.all()

    try:
        events = session.scalars(query).all()
    except ProgrammingError as e:
        print(e)
    for e in events:
        print(
            e.info["reading_logged"]["collection_item_id"],
            e.info["reading_logged"]["emoji"],
        )

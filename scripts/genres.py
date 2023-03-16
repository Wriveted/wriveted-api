# Ensure your environment variables are set such that this script can connect
# directly to the database. E.g. there are different postgres passwords if running
# via docker-compose versus a Cloud SQL database.
import logging
import os
from typing import List

from sqlalchemy import cast, func, select, text, nulls_last, desc
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Edition, Work, BookList
from app.schemas.booklist import BookListItemEnriched
from app.schemas.edition import EditionDetail

logging.basicConfig()
#logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

from app.schemas.class_group import ClassGroupCreateIn

os.environ["POSTGRESQL_SERVER"] = "localhost/"
# os.environ['POSTGRESQL_PASSWORD'] = ''
os.environ["SECRET_KEY"] = ""
# Note we have to set at least the above environment variables before importing our application code

from app import api, config, crud, db, models, schemas
from app.api.dependencies.security import create_user_access_token
from app.db.session import SessionManager, database_connection, get_session_maker


target_genres = """🤓 Factual / Non fiction
😂 Funny
❤️ Romance
👾 Science fiction
🏛️ Historical
✨ Fantasy & Magic
👻 Spooky
😱 Horror
🧐 Mystery & Suspense
🏞️ Adventure and Action
👮 Crime
🎶 Rhymes & Poetry
✍️ Biographical
📒 Diaries
💥 Graphic Novels
🎖️ War
🌋 Dystopian
🇦🇺 Australian
🇺🇸 American
🇬🇧 British
🏈 Sports 
🐒 Animals
""".splitlines()



def extract_genre_labels(info: dict) -> list[str]:
    genres = []
    if 'genres' in info:
        for genre in info['genres']:
            if genre['source'] == 'BISAC':
                # 'JUVENILE FICTION / Social Themes / Emigration & Immigration'
                # 'JUVENILE FICTION / Animals / Dogs'
                # 'JUVENILE FICTION / Historical / Military & Wars'
                if 'Action & Adventure' in genre['name']:
                    genres.append('🏞️ Adventure and Action')
                if 'Animals' in genre['name']:
                    genres.append('🐒 Animals')
                if 'Legends, Myths' in genre['name']:
                    genres.append("✨ Fantasy & Magic")
                if 'Science Fiction' in genre['name']:
                    genres.append('👾 Science fiction')
                if 'biographical' in genre['name']:
                    genres.append('✍️ Biographical')
                if 'Historical' in genre['name']:
                    genres.append('🏛️ Historical')
                if 'Wars' in genre['name']:
                    genres.append('🎖️ War')

            if genre['source'] == 'THEMA':
                # "Children's / Teenage fiction: Action and adventure stories"
                if "Fantasy" in genre['name']:
                    genres.append("✨ Fantasy & Magic")
                if "Action and adventure" in genre['name']:
                    genres.append("🏞️ Adventure and Action")

                if "Humorous stories" in genre['name']:
                    genres.append("😂 Funny")

            if genre['source'] == 'LOCSH':
                if 'Fantasy' in genre['name']:
                    genres.append('✨ Fantasy & Magic')

            if genre['source'] == 'BIC':
                if 'Mysteries' in genre['name']:
                    genres.append('🧐 Mystery & Suspense')
                if 'Humorous stories' in genre['name']:
                    genres.append('😂 Funny')

    return list(set(genres))


settings = get_settings()
engine, SessionLocal = database_connection(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
)

with Session(engine) as session:
    # sample recently liked editions
    recently_liked_isbns = session.scalars(text("""
    with recently_liked_isbns as (
    SELECT
        value->>'isbn' as "isbn",
        value->>'title' as "Title"
    FROM events
    cross join jsonb_array_elements(events.info::jsonb->'reviews')
    WHERE events.title = 'Huey: Books all reviewed' and value->>'liked' = 'true'
    )

    select isbn from recently_liked_isbns where length(isbn) > 1 limit 50;
    """)).all()

    editions: List[Edition] = session.scalars(
        select(Edition).where(Edition.isbn.in_(recently_liked_isbns))
    ).all()


    for e in editions[:10]:
        existing_labelset = e.work.labelset

        genres = extract_genre_labels(e.info)

        print(e.title, ' - ', e.work.get_authors_string())
        print(','.join(genres))
        print()

import json
import os
from typing import List
os.environ["POSTGRESQL_SERVER"] = "localhost/"
import openai

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Edition
from app.db.session import database_connection


system_prompt = """You are a book classifier. You are given a book and you need to label it from the following genres:
🤓 Factual / Non fiction
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

You are given structured data from multiple sources, including the book's title, one or more descriptions
and genre labels. You can use this data to help you classify the book. Your output should be JSON
with the following keys: 'description', 'genres'. The 'genres' key should be a list of genres as above.

Optionally include a 'series' key with the name of the series the book is part of.
"""

def extract_genre_labels(edition: Edition):
    huey_summary = edition.work.labelset.huey_summary

    genre_data = []
    for g in edition.info.get('genres', []):
        genre_data.append(f"{g['source']};{g['name']}")
    genre_data = '\n'.join(genre_data)

    user_content = f"""The book is called '{edition.title}' by {edition.work.get_authors_string()}. 
    
    Current descriptions:
    
    - {huey_summary}
    - {edition.info.get('summary_short')}
    - {edition.info.get('summary_long')}
    
    Current genres:
    
    {genre_data}
    
    """

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
            # {"role": "assistant", "content": "Who's there?"},
            # {"role": "user", "content": "Orange."},
        ],
        temperature=0,
    )

    print(response['usage']['total_tokens'])
    print(response['choices'][0]['message']['content'])

    return json.loads(response['choices'][0]['message']['content'].strip())



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


    for e in editions[:3]:
        existing_labelset = e.work.labelset

        output = extract_genre_labels(e)

        print(e.title, ' - ', e.work.get_authors_string())
        print(output)

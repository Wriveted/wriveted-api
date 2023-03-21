import json
import os
from textwrap import dedent
from typing import List

os.environ["POSTGRESQL_SERVER"] = "localhost/"
import openai
from rich import print

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Edition
from app.db.session import database_connection


system_prompt = """You are a children's librarian assistant. You are given book data and you need to provide a summary suitable 
for children and parents.

You are given structured data from multiple semi-reliable sources, including the book's title, one or more descriptions
and genre labels. You can use this data to help you describe the book.
 
The short description should be approximately 1 to 2 sentences long, friendly. Do not mention the title or start with the title in the short description. 
The language should appeal to a 9 year old. Example short description:
- Harry and his dog Hopper have done everything together, ever since Hopper was a jumpy little puppy. But one day the unthinkable happens. Harry comes home from school... and Hopper isn't there to greet him.
- Something strange is happening in Alfie's town. Instead of shiny coins from the Tooth Fairy, kids are waking up to dead slugs, live spiders, and other dreadfully icky things under their pillows. Who would do something so horrific?
- Twelve-year-old Percy is sent to a summer camp for demigods like himself, and joins his new friends on a quest to prevent a war between the gods.

The long description should be friendly and aimed at an adult reader. Don't mention the title or the fact that it is a story or a book. It is okay to mention any awards in the long description.
Pay attention to the title of the book for clues as to what is important to mention, a good long description might mention the characters, their relationships, and the events that take place.

Both descriptions should not be patronising. Do not try to sell or use sales language e.g. 'bestseller', 'must read'. Don't mention books by other authors.
Don't use US or UK specific language - e.g. don't mention middle grade. Don't mention the number of pages.

The reading ability should be a number between 1 and 5. Examples for each level including lexiles are:
- 1 easy picture book such as "Where's Spot" by Eric Hill. 160L
- 2 "Cat in the Hat" by Dr. Seuss. 430L
- 3 "Treehouse" by Andy Griffiths. 560L
- 4 "Charlie and the Chocolate Factory" by Roald Dahl. 810L
- 5 "Harry Potter and the Philosopher's Stone". 880L

'hues' should contain a list of these and only these labels:
- "hue01_dark_suspense" for Dark/Suspense
- "hue02_beautiful_whimsical" for Beautiful/Whimsical
- "hue03_dark_beautiful" for Dark/Beautiful
- "hue05_funny_comic" for Funny/Comic
- "hue06_dark_gritty" for Dark/Gritty
- "hue07_silly_charming" for Silly/Charming
- "hue08_charming_inspiring" for Charming/Inspiring
- "hue09_charming_playful" for Charming/Playful
- "hue10_inspiring" for Inspiring
- "hue11_realistic_hope" for Realistic/Hope
- "hue12_funny_quirky" for Funny/Quirky
- "hue13_straightforward" for Straightforward very little tone, just straightforward explanations.


Your output should be JSON with the following keys: 'long-description', 'short-description', 'minimum-age', 'maximum-age', 'reading-ability', 'hues'

Optionally include:
- 'lexile' with the lexile score of the book,
- a 'series' key with the name of the series the book is part of,
- a 'series-number' key with the number of the book in the series,
- 'awards' with a list of awards the book has won, 
- 'notes' with any other brief information you think is relevant for parents and other librarians such as content advisory. Adult themes, heavy emotional content, religion and LGBTQ themes should also be noted. Similar to movie and streaming classification systems.
- 'hues' a list of hues as described above.
"""


def extract_genre_labels(edition: Edition, related_editions: List[Edition]):
    huey_summary = edition.work.labelset.huey_summary

    genre_data = set()
    for e in related_editions:

        for g in e.info.get("genres", []):
            genre_data.add(f"{g['source']};{g['name']}")
    genre_data = "\n".join(genre_data)

    short_summaries = set()
    for e in related_editions:
        short_summaries.add(e.info.get("summary_short"))

    short_summaries = "\n".join(f"- {s}" for s in short_summaries if s is not None)

    user_content = dedent(
        f"""The book is called '{edition.title}' by {edition.work.get_authors_string()}. 
    
    Current short descriptions:
    
    - {huey_summary}
    {short_summaries}
    
    Detailed Description:
    {edition.info.get('summary_long')}

    Keywords:
    {edition.info.get('keywords')}
    
    Other info:
    - {edition.info.get('cbmctext')}
    - {edition.info.get('prodct')}

    - Number of pages: {edition.info.get('pages')}
    
    Current genres:
    
    {genre_data}
    
    Remember your output should only contain JSON with the following keys: 'long-description', 'short-description', 'minimum-age', 'maximum-age', 'lexile',
    'reading-ability' and the following optional keys: 'series', 'series-number', 'awards', 'notes'
    """
    )

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

    # print(response['usage']['total_tokens'])
    # print(response['choices'][0]['message']['content'])

    return response["usage"]["total_tokens"], json.loads(
        response["choices"][0]["message"]["content"].strip()
    )


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

    for e in editions[:20]:
        existing_labelset = e.work.labelset
        print()
        print(f"[red] {e.title} by {e.work.get_authors_string()} (ISBN: {e.isbn})")

        related_editions = [
            ed
            for ed in e.work.editions[:20]
            if ed.info is not None and ed.title == e.title
        ]

        tokens, output = extract_genre_labels(e, related_editions)

        total_tokens += tokens
        # output['huey_min_age'] = e.work.labelset.min_age
        # output['huey_max_age'] = e.work.labelset.max_age
        # output['huey_existing_summary'] = e.work.labelset.huey_summary
        # output['huey_existing_long_summary'] = e.info.get('summary_long')

        print(f"[green] {tokens} tokens used, {total_tokens} total tokens")
        print(f"[blue]", output)

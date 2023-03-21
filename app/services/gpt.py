import json
from textwrap import dedent
from app.config import get_settings
from app.models.work import Work
import openai

settings = get_settings()

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
- 3 "Treehouse" series by Andy Griffiths. 560L
- 4 "Charlie and the Chocolate Factory" by Roald Dahl. 810L
- 5 "Harry Potter and the Philosopher's Stone". 880L

-----

'hues' should contain a mapping of these and only these labels, depending on how strongly the book fits the tones expressed by the label:
- "hue01_dark_suspense": Dark, often mysterious, these books are suspenseful and adventurous.
- "hue02_beautiful_whimsical": Beautiful worlds with kooky or offbeat characters.
- "hue03_dark_beautiful": These stories are dark, beautiful, and often heartbreaking.
- "hue04_charming_emotional": Charming, inspiring and joyful books that help us explore human emotions and experiences.
- "hue05_funny_comic": Purely funny books! Often have a comic illustration style, but are not just comic books.
- "hue06_dark_gritty": Grim, serious books that take you to the dark side of humanity. Usually for older readers.
- "hue07_silly_charming": Charming , funny books that are a little bit slapstick and active. Often for preschoolers.
- "hue08_charming_inspiring": Winsome, whimsical and resilient characters set in adventurous and chaming or beautiful stories.
- "hue09_charming_playful": Charming and playful, these books are gentle and a little funny.
- "hue10_inspiring": Beautiful, inspiring books, evocative and sometimes based in reality.
- "hue11_realistic_hope": Realistic characters with relatable problems. These are often coming of age books.
- "hue12_funny_quirky": Funny and a little offbeat. These books have a quirk that is a little witty or strange.
- "hue13_straightforward": Informative/Factual books with very little tone. Encyclopaedic or factual books.

a rough example of a hue mapping for Harry Potter and the Philosopher's Stone:
{
    "hue01_dark_suspense": 0.4,
    "hue02_beautiful_whimsical": 0.9,
    "hue03_dark_beautiful": 0.3,
    "hue04_charming_emotional": 0.8,
    "hue05_funny_comic": 0.3,
    "hue06_dark_gritty": 0.2,
    "hue07_silly_charming": 0.5,
    "hue08_charming_inspiring": 0.7,
    "hue09_charming_playful": 0.5,
    "hue10_inspiring": 0.8,
    "hue11_realistic_hope": 0.6,
    "hue12_funny_quirky": 0.3,
    "hue13_straightforward": 0.2
}

The values should be between 0 and 1, and can be up to two decimal places. 
The higher the value, the more strongly the book fits the tone expressed by the label.

-----

'gender' should be whichever of the following keys is most appropriate, relating to the main character(s) of the book. If it is unclear, leave it blank.
- "male"
- "female"
- "non-binary"

-----

'characters' should contain a list of these and only these labels, relating to the main character(s) of the book. A reasonable number of labels should be used, but not too many.
- "Bugs"
- "Cats, Dogs and Mics"
- "Horses and farm animals"
- "Ocean creatures"
- "Wolves and Wild animals"
- "Australian Animals"
- "Dinosaurs"
- "Princesses, Fairies, Mermaids"
- "Unicorns"
- "Superheroes"
- "Families and friends"
- "Monsters, Ghosts and Vampires"
- "Aliens"
- "Trains, Cars and Trucks"
- "Misfits and underdogs"
- "Pirates"
- "Robots"

-----

Your output should be JSON with the following keys: 'long-description', 'short-description', 'minimum-age', 'maximum-age', 'reading-ability', 'hues'

Optionally include:
- 'lexile' with the lexile score of the book,
- a 'series' key with the name of the series the book is part of,
- a 'series-number' key with the number of the book in the series,
- 'awards' with a list of awards the book has won, 
- 'notes' with any other brief information you think is relevant for parents and other librarians such as content advisory. Adult themes, heavy emotional content, religion and LGBTQ themes should also be noted. Similar to movie and streaming classification systems.
- 'hues' a mapping of hues as described above.
- 'gender' a single key as described above.
- 'characters' a list of character types as described above.

"""


def extract_labels(work: Work):
    editions = [
        ed
        for ed in work.editions[:20]
        if ed.info is not None and ed.title == work.title
    ]
    main_edition = editions[0]

    huey_summary = work.labelset.huey_summary

    genre_data = set()
    for e in editions[:20]:
        for g in e.info.get("genres", []):
            genre_data.add(f"{g['source']};{g['name']}")
    genre_data = "\n".join(genre_data)

    short_summaries = set()
    for e in editions:
        short_summaries.add(e.info.get("summary_short"))

    short_summaries = "\n".join(f"- {s}" for s in short_summaries if s is not None)

    user_content = dedent(
        f"""The book is called '{work.get_display_title()}' by {work.get_authors_string()}.
    
            Current short descriptions:
            
            - {huey_summary}
            {short_summaries}
            
            Detailed Description:
            {main_edition.info.get('summary_long')}

            Keywords:
            {main_edition.info.get('keywords')}
            
            Other info:
            - {main_edition.info.get('cbmctext')}
            - {main_edition.info.get('prodct')}

            - Number of pages: {main_edition.info.get('pages')}
            
            Current genres:
            
            {genre_data}
            
            Remember your output should only contain JSON with the following keys: 
            'long-description', 
            'short-description', 
            'minimum-age', 
            'maximum-age', 
            'lexile',
            'reading-ability',
            'genres',
            and the following optional keys: 
            'series', 
            'series-number', 
            'awards', 
            'notes'
            """
    )

    openai.api_key = settings.OPENAI_API_KEY

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

    try:
        response_string = response["choices"][0]["message"]["content"].strip()
        # Try to parse the response string as JSON
        json_data = json.loads(response_string)
    except ValueError:
        # If the response string is not valid JSON, try to extract the JSON string
        try:
            json_start = response_string.index("{")
            json_end = response_string.rindex("}") + 1
            json_data = json.loads(response_string[json_start:json_end])
        except ValueError:
            return response["usage"], {
                "error": "Could not extract JSON from response string"
            }

    return response["usage"], json_data

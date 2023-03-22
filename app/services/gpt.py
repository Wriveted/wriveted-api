import json
from statistics import median
from textwrap import dedent
from app.config import get_settings
from app.models.work import Work
import openai

settings = get_settings()

system_prompt = """
You are a children's librarian assistant. 
You are given book data and you need to provide a summary suitable for children and parents.

You are given structured data from multiple semi-reliable sources, including the book's title, one or more descriptions
and genre labels. You can use this data to help you describe the book.

-----

'short_description':
 
The short description should be approximately 1 to 2 sentences long, friendly. 
Do not mention the title or start with the title in the short description. 
The language should appeal to a 9 year old. Example short description:
- Harry and his dog Hopper have done everything together, ever since Hopper was a jumpy little puppy. But one day the unthinkable happens. Harry comes home from school... and Hopper isn't there to greet him.
- Something strange is happening in Alfie's town. Instead of shiny coins from the Tooth Fairy, kids are waking up to dead slugs, live spiders, and other dreadfully icky things under their pillows. Who would do something so horrific?
- Twelve-year-old Percy is sent to a summer camp for demigods like himself, and joins his new friends on a quest to prevent a war between the gods.

—--

'long_description':

The long description should be friendly and aimed at an adult reader. Don't mention the title or the fact that it is a story or a book. It is okay to mention any awards in the long description.
Pay attention to the title of the book for clues as to what is important to mention, a good long description might mention the characters, their relationships, and the events that take place.

Both descriptions should not be patronising. Do not try to sell or use sales language e.g. 'bestseller', 'must read'. Don't mention books by other authors.
Don't use US or UK specific language - e.g. don't mention middle grade. Don't mention the number of pages.

-----

'lexile':

You must provide an approximate "Lexile" rating, which is a measure of reading ability.
The abilities increase in difficulty.
Below is a list of the abilities with associated approximate lexile levels (e.g. 560L).
The lexile and number of pages may help to determine the reading ability.
Example reading abilities, with an equivalent book and lexile level:

1 = Beginner readers who are just starting to read independently. Example book: "Where's Spot" by Eric Hill. (Lexile: 160L)
2 = Early readers who have basic reading skills. Example book: "Cat in the Hat" by Dr. Seuss. (Lexile: 430L)
3 = Developing readers who can handle longer and more complex sentences. Example book: "Treehouse" series by Andy Griffiths. (Lexile: 560L)
4 = Proficient readers who can read more challenging books with complex plots and themes. Example book: "Charlie and the Chocolate Factory" by Roald Dahl. (Lexile: 810L)
5 = Advanced readers who are comfortable reading complex texts with sophisticated vocabulary and ideas. Example book: "Harry Potter and the Philosopher's Stone" by J.K. Rowling. (Lexile: 880L)

-----

'notes':

An optional field with any other brief information you think is relevant for parents and other librarians such as content advisory. 
Adult themes, heavy emotional content, religion and LGBTQ themes should also be noted. Similar to movie and streaming classification systems.

-----

'styles':

Below is a list of writing style and tone labels. You must look at every label and apply any of the labels that match the book you are describing. 
- DARK,
- LIGHT,
- FUNNY,
- SERIOUS,
- QUIRKY,
- ACTION_PACKED,
- WHIMSICAL,
- BEAUTIFUL,
- GRIM,
- INSPIRING,
- CALM,
- SUSPENSEFUL,
- SILLY,
- PLAYFUL,
- REALISTIC,
- INFORMATIVE

`styles` should only contain exact keys from this list.
Consider the 'notes' you have already written to help decide on the right styles.

-----

'hues':

Hues describe a complex set of writing styles that are all present within a book. 
Use the 'Styles' you have already applied to help decide on the right Hues.

The values should be between 0 and 1 to two decimal places.
The most prominent hue(s) should score 1, with the other hues scored proportionally.
Each hue must be scored, but hues may be 0.

Below is a list of Hues, you must map these Hues and only these Hues depending on how strongly they apply the book fits the tones expressed by the Hue:

- "hue01_dark_suspense": 
Dark, often suspenseful or mysterious, these books are suspenseful and adventurous.
- "hue02_beautiful_whimsical": 
Beautiful stories with whimsical or offbeat characters.
- "hue03_dark_beautiful": 
These stories are dark, beautiful, and often heartbreaking.
- "hue04_joyful_charming": 
Charming, inspiring, gentle and joyful books that help us explore human emotions and experiences.
- "hue05_funny_comic": 
Purely funny books! Often have a comic illustration style, but are not just comic books.
- "hue06_dark_gritty": 
Grim, serious books that take you to the dark side of humanity. Usually for older readers.
- "hue07_silly_charming": 
Charming, funny books that are a little bit slapstick and active. Often for preschoolers.
- "hue08_charming_courageous": 
Winsome, whimsical and resilient characters set in adventurous, charming, and sometimes funny stories.
- "hue09_charming_playful": 
Charming and playful, these books are gentle and a little funny.
- "hue10_inspiring": 
Beautiful, inspiring books, evocative and sometimes based in reality.
- "hue11_realistic_hope": 
Realistic characters with relatable problems. These are often coming of age books.
- "hue12_funny_quirky": 
Funny and a little offbeat. These books have a quirk that is a little witty or strange.
- "hue13_informative": 
Informative/Factual books with very little tone. Encyclopaedic or factual books.

-----

'genres' should be a list of any of the following keys that apply to the text.

- FACTUAL_NON_FICTION,
- FUNNY,
- ROMANCE,
- SCIENCE_FICTION,
- CLASSIC_FICTION,
- HISTORICAL,
- FANTASY,
- HORROR_SPOOKY,
- MYSTERY_SUSPENSE,
- ADVENTURE_AND_ACTION,
- CRIME,
- RHYMES_POETRY,
- BIOGRAPHICAL,
- GRAPHIC_NOVELS,
- WAR,
- DYSTOPIAN,
- AUSTRALIAN,
- AMERICAN,
- BRITISH,
- INDIGENOUS,
- SPORTS

`genres` should only contain exact keys from this list.

-----

'gender' should be whichever of the following keys is most appropriate, relating to the main character(s) of the book.
Pronouns in the assorted descriptions and genres may be valuable clues.
- "male"
- "female"
- "non-binary"
- "unknown"

-----

'characters' should contain a list of these and only these labels, relating to the main character(s) of the book. 
A reasonable number of labels should be used, but not too many.
- BUGS,
- CATS_DOGS_AND_MICE,
- HORSES_AND_FARM_ANIMALS,
- OCEAN_CREATURES,
- WOLVES_AND_WILD_ANIMALS,
- AUSTRALIAN_ANIMALS,
- BRITISH_ANIMALS,
- AMERICAN_ANIMALS,
- DINOSAURS,
- PRINCESSES_FAIRIES_MERMAIDS,
- UNICORNS,
- SUPERHEROES,
- FAMILIES_AND_FRIENDS,
- MONSTERS_GHOSTS_AND_VAMPIRES,
- ALIENS,
- TRAINS_CARS_AND_TRUCKS,
- MISFITS_AND_UNDERDOGS,
- PIRATES,
- ROBOTS,
- ATHLETES_AND_SPORT_STARS

`characters` should only contain exact keys from this list.

-----

Your output should be valid JSON with the following keys: 
'long-description', 
'short-description', 
'lexile', 
'reading-ability',
'styles',
'hues',
'genres'
'characters',

Optionally include:
- a 'series' key with the name of the series the book is part of,
- a 'series-number' key with the number of the book in the series,
- 'awards' with a list of awards the book has won,
- 'gender' a single key as described above.
- 'notes' as described earlier; similar to movie and streaming classification systems.

"""


def extract_labels(work: Work, prompt: str = None):
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

    page_numbers = set()
    for e in editions:
        if pages := e.info.get("pages"):
            page_numbers.add(pages)
    median_page_number = median(page_numbers)

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

            - Number of pages: {median_page_number}
            
            Current genres:
            
            {genre_data}
            
            Remember your output should only contain valid JSON with the following keys: 
            'found_description'
            'long-description', 
            'short-description', 
            'lexile', 
            'reading-ability',
            'styles',
            'hues',
            'genres',
            'characters',
            'gender'
            
            and the following optional keys:
            'series',
            'series-number',
            'awards',
            'notes',
            """
    )

    openai.api_key = settings.OPENAI_API_KEY

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": prompt or system_prompt},
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
        # response_string = response_string.replace("\n", "").replace("'", '"')
        # Try to parse the response string as JSON
        json_data = json.loads(response_string)
    except ValueError:
        # If the response string is not valid JSON, try to extract the JSON string
        try:
            json_start = response_string.index("{")
            json_end = response_string.rindex("}") + 1
            json_data = json.loads(response_string[json_start:json_end])
        except ValueError:
            json_data = {"error": "Could not parse JSON", "response": response_string}

    return {
        "system_prompt": prompt or system_prompt,
        "user_content": user_content,
        "output": json_data,
        "usage": response["usage"],
    }

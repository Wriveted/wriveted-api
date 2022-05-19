import csv
import os
import random
from structlog import get_logger
from sqlalchemy.orm import Session
from app import crud

logger = get_logger()


class WordListItem:
    adjective: str
    colour: str
    noun: str


class WordList:
    def __init__(self):
        here = os.path.dirname(os.path.abspath(__file__))
        # current csv capable of 11*11*11*100 ≈ 130k names
        self.filename = os.path.join(here, "wordlist.csv")

    def __enter__(self):
        self.file = open(self.filename)
        data = csv.DictReader(self.file)
        wordlist = list(data)
        return wordlist

    def __exit__(self, exc_type, exc_value, traceback):
        self.file.close()


def new_random_username(
    session: Session,
    wordlist: list[WordListItem],
    adjective: bool = False,
    colour: bool = True,
    noun: bool = True,
    numbers: int = 2,
    slugify: bool = False,
):
    """
    Generates a new random username of the specified or default complexity,
    ensuring it's not already claimed by a user.
    Default complexity: ColourNounNumber (RedWolf52)

    """

    if not (adjective or colour or noun or numbers):
        raise ValueError(
            "Must enable at least one username constituent (adjective, colour, noun, numbers)"
        )

    name = ""
    name_valid = False

    while not name_valid:
        name = generate_random_username_from_wordlist(
            wordlist, adjective, colour, noun, numbers, slugify
        )
        name_valid = name and crud.user.get_by_username(session, name) is None

    return name


def generate_random_username_from_wordlist(
    wordlist: list[
        WordListItem
    ],  # array of dicts, assuming the csv is consumed outside of this func
    adjective: bool,  # whether or not to include an adjective
    colour: bool,  # whether or not to include a colour
    noun: bool,  # whether or not to include a noun
    numbers: int,  # suffix with how many digits
    slugify: bool,  # whether or not to lowercase and hyphenate the username
) -> str:
    name = ""
    slug = "-" if slugify else ""

    if adjective:
        name += random.choice(wordlist)["adjective"].title()
    if colour:
        name += (slug if name else "") + random.choice(wordlist)["colour"].title()
    if noun:
        name += (slug if name else "") + random.choice(wordlist)["noun"].title()
    if numbers:
        name += (slug if name else "") + "".join(
            [str(random.randint(0, 9)) for i in range(numbers)]
        )

    return name if not slugify else name.lower()

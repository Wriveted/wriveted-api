import csv
import os
import random
from structlog import get_logger
from sqlalchemy.orm import Session
from app import crud

logger = get_logger()

# generates a new random username of the specified or default complexity,
# ensuring it's not already claimed by a user.
# default complexity: ColourNounNumber (RedWolf52)
def new_random_username(
    session: Session,
    adjective: bool = False,
    color: bool = True,
    noun: bool = True,
    numbers: int = 2,
    slugify: bool = False,
):
    name = ""
    valid_name = False

    here = os.path.dirname(os.path.abspath(__file__))
    # current csv capable of 11*11*11*99 ≈ 130k names
    filename = os.path.join(here, "wordlist.csv")
    with open(filename) as f:
        data = csv.DictReader(f)
        wordlist = list(data)

        while not valid_name:
            name = generate_random_username_from_wordlist(
                wordlist, adjective, color, noun, numbers, slugify
            )
            valid_name = (
                name is not None and crud.user.get_by_username(session, name) is None
            )

    return name


class WordListItem:
    adjective: str
    colour: str
    noun: str


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

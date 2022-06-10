import csv
import os
import random

from pydantic import BaseModel
from sqlalchemy.orm import Session
from structlog import get_logger

from app.models import Student

logger = get_logger()


def generate_random_users(session: Session, num_users: int, school_id: int, **kwargs):
    """
    Generate `num_users` new users with random usernames.

    Any additional `kwargs` are passed directly to the `User` model, so
    to add 100 students to a particular school:

    >>> generate_random_users(session, 100, school_as_student=some_school, type=UserAccountType.STUDENT)

    By default, `name` is set to a blank string, `is_active` is set to False. Pass
    alternatives as kwargs.

    Note this function adds users to the current transaction, but doesn't
    commit the transaction.
    """

    # Default user arguments:
    user_kwargs = {
        "name": "",
        "is_active": False,
    }
    user_kwargs.update(kwargs)
    new_users = []
    with WordList() as wordlist:
        for i in range(num_users):
            username = new_random_username(
                session=session, wordlist=wordlist, school_id=school_id
            )
            user = Student(username=username, school_id=school_id, **user_kwargs)
            session.add(user)
            session.flush()
            new_users.append(user)
    return new_users


class WordListItem(BaseModel):
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
        wordlist = [WordListItem(**item) for item in data]
        return wordlist

    def __exit__(self, exc_type, exc_value, traceback):
        self.file.close()


def new_random_username(
    session: Session,
    school_id: int,
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
    from app import crud

    if not (adjective or colour or noun or numbers):
        raise ValueError(
            "Must enable at least one username constituent (adjective, colour, noun, numbers)"
        )

    name = ""
    name_valid = False
    attempts_remaining = 1000

    while not name_valid and attempts_remaining > 0:
        name = generate_random_username_from_wordlist(
            wordlist, adjective, colour, noun, numbers, slugify
        )
        name_valid = (
            name
            and crud.user.get_student_by_username_and_school_id(
                session, name, school_id
            )
            is None
        )
        attempts_remaining -= 1

    if attempts_remaining == 0:
        raise ValueError("Couldn't generate a random user name")

    return name


def new_identifiable_username(
    first_name: str, last_name_initial: str, session, school_id: int
):
    """
    Generates a new identifiable username using Reader's first name and initial of last name,
    ensuring it's not already claimed by another user.
    Appends with digits for extra entropy.
    """
    from app import crud

    username_base = (first_name + last_name_initial).replace(" ", "")
    username = username_base
    username_valid = False
    attempts_remaining = 1000

    while not username_valid and attempts_remaining > 0:
        username = username_base + str(random.randint(10, 99))
        username_valid = (
            username
            and crud.user.get_student_by_username_and_school_id(
                session, username, school_id
            )
            is None
        )
        attempts_remaining -= 1

    if attempts_remaining == 0:
        raise ValueError("Couldn't generate a unique username for Reader")

    return username


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
        name += random.choice(wordlist).adjective.title()
    if colour:
        name += (slug if name else "") + random.choice(wordlist).colour.title()
    if noun:
        name += (slug if name else "") + random.choice(wordlist).noun.title()
    if numbers:
        name += (slug if name else "") + "".join(
            [str(random.randint(0, 9)) for i in range(numbers)]
        )

    return name if not slugify else name.lower()

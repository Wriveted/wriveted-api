import csv
import random
from structlog import get_logger
from sqlalchemy.orm import Session

from app import crud

logger = get_logger()

# default complexity: ColourNounNumber (RedWolf52)
async def new_random_username(
    session: Session,
    adjective: bool = False,
    color: bool = True,
    noun: bool = True,
    numbers: int = 0,
):
    name = ""
    valid_name = False

    with open("wordlist.csv") as f:
        wordlist = csv.reader(f)

        while not valid_name:
            name = generate_random_username_from_csv(
                wordlist, adjective, color, noun, numbers
            )
            valid_name = name is not None and crud.user.get_by_username(name) is None

    return name


# expects column headers 'adjective', 'colour', 'noun'
def generate_random_username_from_csv(
    csv, adjective: bool, colour: bool, noun: bool, numbers: int
) -> str:
    rows = list(csv)
    name = ""
    if adjective:
        name = name + random.choice(rows)["adjective"]
    if colour:
        name = name + random.choice(rows)["colour"]
    if noun:
        name = name + random.choice(rows)["noun"]
    if numbers:
        name = name + "".join([str(random.randint(0, 9)) for i in range(numbers)])

    return name

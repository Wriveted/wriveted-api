from typing import List
from sqlalchemy import select
from structlog import get_logger
from app import crud
from app.models import Edition
from sqlalchemy.orm import Session
from app.schemas.edition import EditionCreateIn

logger = get_logger()


async def compare_known_editions(session, isbn_list: List[str]):
    known_matches: list[Edition] = (
        session.execute(crud.edition.get_multi_query(db=session, ids=isbn_list))
        .scalars()
        .all()
    )
    fully_tagged_matches = 0
    for e in known_matches:
        try:
            if e.work.labelset.checked == True:
                fully_tagged_matches += 1
        except Exception as e:
            # print(e)
            continue

    return len(known_matches), fully_tagged_matches


async def create_missing_editions(session, new_edition_data: list[EditionCreateIn]):
    isbns = {get_definitive_isbn(e.isbn) for e in new_edition_data if len(e.isbn) > 0}
    existing_isbns = (
        session.execute(select(Edition.isbn).where((Edition.isbn).in_(isbns)))
        .scalars()
        .all()
    )
    isbns_to_create = isbns.difference(existing_isbns)
    logger.info(f"Will have to create {len(isbns_to_create)} new editions")

    new_editions_hydrated = []
    new_editions_unhydrated = []

    for data in new_edition_data: 
        if data.isbn in isbns_to_create:
            if data.work_info is not None:
                new_editions_hydrated.append(data)
            else:
                new_editions_unhydrated.append(data)
    
    if len(new_editions_hydrated > 0):
        crud.edition.create_in_bulk(session, bulk_edition_data=new_editions_hydrated)
        logger.info("Created new hydrated editions")

    if len(new_editions_unhydrated > 0):
        crud.edition.create_in_bulk_unhydrated(session, bulk_edition_data=new_editions_unhydrated)
        logger.info("Created new unhydrated editions")

    return isbns, isbns_to_create, existing_isbns


async def create_missing_editions_unhydrated(session: Session, isbn_list: list[str]):
    final_primary_keys = await crud.edition.create_in_bulk_unhydrated(session, isbn_list=isbn_list)
    return final_primary_keys


# http://www.niso.org/niso-io/2020/01/new-year-new-isbn-prefix
# https://www.isbn.org/about_isbn_standard
# https://bisg.org/news/479346/New-979-ISBN-Prefixes-Expected-in-2020.htm
# It seems that any ISBN10 has an equivalent ISBN13(978) and vice versa, but also:
# no ISBN10 has an equivalent ISBN13(979), and vice versa.
# Since *every* ISBN is representable as ISBN13, but not *every* ISBN is representable as ISBN10,
# all Editions should be stored by ISBN13, and any queries should standardise the request into
# a "definitive" isbn to store or lookup.
def get_definitive_isbn(isbn: str):
    # strip all characters that aren't "valid" (i.e. hyphens, spaces)
    valid_chars = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "X"]
    cleaned_isbn = "".join([i for i in isbn if i in valid_chars])

    assert len(cleaned_isbn) > 0

    # append leading zeroes to make at least 10 chars 
    # (sometimes leading zeroes can be stripped from valid isbn's by excel or the like)
    cleaned_isbn = cleaned_isbn.zfill(10)

    assert isbn_is_valid(cleaned_isbn)

    if len(cleaned_isbn) == 10:
        return convert_10_to_13(cleaned_isbn)
    elif len(cleaned_isbn) == 13:
        return cleaned_isbn


def clean_isbns(isbns: list[str]) -> set[str]:
    cleaned_isbns = set()
    for isbn in isbns:
        try:
            cleaned_isbns.add(get_definitive_isbn(isbn))
        except:
            continue
    return cleaned_isbns


# --- courtesy of https://code.activestate.com/recipes/498104-isbn-13-converter/ ---

def isbn_is_valid(isbn):
    if(len(isbn) not in [10,13]): 
        return False

    body = isbn[:-1]
    check = isbn[-1]

    return (check_digit_10(body) == check) \
        if len(isbn) == 10 \
        else (check_digit_13(body) == check)


def check_digit_10(isbn):
    assert len(isbn) == 9
    sum = 0
    for i in range(len(isbn)):
        c = int(isbn[i])
        w = i + 1
        sum += w * c
    r = sum % 11
    if r == 10:
        return "X"
    else:
        return str(r)


def check_digit_13(isbn):
    assert len(isbn) == 12
    sum = 0
    for i in range(len(isbn)):
        c = int(isbn[i])
        if i % 2:
            w = 3
        else:
            w = 1
        sum += w * c
    r = 10 - (sum % 10)
    if r == 10:
        return "0"
    else:
        return str(r)


def convert_10_to_13(isbn):
    assert len(isbn) == 10
    prefix = "978" + isbn[:-1]
    check = check_digit_13(prefix)
    return prefix + check


#  ---------------------------------------------------------------------------------

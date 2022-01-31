from typing import List
from sqlalchemy import select
from structlog import get_logger
from app import crud
from app.models import Edition

logger = get_logger()


async def compare_known_editions(session, isbn_list: List[str]):
    known_matches: list[Edition] = session.execute(crud.edition.get_multi_query(db=session, ids=isbn_list)).scalars().all()
    fully_tagged_matches = []
    for e in known_matches:
        try:
            if e.work.labelset.checked == True:
                fully_tagged_matches.append(e)
        except Exception as e:
            # print(e)
            continue

    return len(known_matches), len(fully_tagged_matches)



async def create_missing_editions(session, new_edition_data):
    isbns = {get_definitive_isbn(e.ISBN) for e in new_edition_data if len(e.ISBN) > 0}
    existing_isbns = session.execute(select(Edition.ISBN).where((Edition.ISBN).in_(isbns))).scalars().all()
    isbns_to_create = isbns.difference(existing_isbns)
    logger.info(f"Will have to create {len(isbns_to_create)} new editions")
    new_edition_data = [data for data in new_edition_data if data.ISBN in isbns_to_create]
    crud.edition.create_in_bulk(session, bulk_edition_data=new_edition_data)
    logger.info("Created new editions")
    return isbns, isbns_to_create, existing_isbns



# http://www.niso.org/niso-io/2020/01/new-year-new-isbn-prefix
# https://www.isbn.org/about_isbn_standard
# https://bisg.org/news/479346/New-979-ISBN-Prefixes-Expected-in-2020.htm
# It seems that any ISBN10 has an equivalent ISBN13(978) and vice versa, but also:
# no ISBN10 has an equivalent ISBN13(979), and vice versa.
# Since *every* ISBN is representable as ISBN13, but not *every* ISBN is representable as ISBN10,
# all Editions should be stored by ISBN13, and any queries should standardise the request into 
# a "definitive" isbn to store or lookup.
def get_definitive_isbn(isbn: str):
    valid_chars = ['0','1','2','3','4','5','6','7','8','9','X']
    # strip all characters that aren't "valid" (i.e. hyphens, spaces)
    cleaned_isbn = ''.join([i for i in isbn if i in valid_chars])
    cleaned_isbn = cleaned_isbn.zfill(10)
    assert len(cleaned_isbn) in [10, 13]
    if len(cleaned_isbn) == 10:
        return convert_10_to_13(cleaned_isbn)
    elif len(cleaned_isbn) == 13:
        return cleaned_isbn


# --- courtesy of https://code.activestate.com/recipes/498104-isbn-13-converter/ ---

def check_digit_10(isbn):
    assert len(isbn) == 9
    sum = 0
    for i in range(len(isbn)):
        c = int(isbn[i])
        w = i + 1
        sum += w * c
    r = sum % 11
    if r == 10: return 'X'
    else: return str(r)

def check_digit_13(isbn):
    assert len(isbn) == 12
    sum = 0
    for i in range(len(isbn)):
        c = int(isbn[i])
        if i % 2: w = 3
        else: w = 1
        sum += w * c
    r = 10 - (sum % 10)
    if r == 10: return '0'
    else: return str(r)

def convert_10_to_13(isbn):
    assert len(isbn) == 10
    prefix = '978' + isbn[:-1]
    check = check_digit_13(prefix)
    return prefix + check

#  ---------------------------------------------------------------------------------
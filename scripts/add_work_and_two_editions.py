from enum import Enum
import os
import base64
from time import sleep, time
from io import BytesIO
from PIL import Image
from xml.etree import ElementTree as ET
import httpx
from tomlkit import key
from examples.config import settings

class NielsenQueryType(Enum):
    INFO = 0
    IMAGE = 2

def nielsen_query(isbn:str, queryType:NielsenQueryType):
    response: httpx.Response = httpx.get(
        settings.NIELSEN_API,
        params={
            'clientId': settings.NIELSEN_CLIENT_ID,
            'password': settings.NIELSEN_CLIENT_PASSWORD,
            'from': 0,
            'to': 1,
            'indexType': queryType.value,
            'format': 7,
            'resultView': 2,
            'field0': 1,
            'value0': isbn
        }
    )
    raw_response_content = '<?xml version="1.0" encoding="ISO-8859-1"?>' + response.content.decode('UTF-8').replace('<?xml version="1.0" encoding="ISO-8859-1"?>','')
    xml_tree = ET.fromstring(raw_response_content)

    try:
        result_code = xml_tree.find('resultCode').text
        print(result_code)

        if result_code == '50':
            print("rate limit reached :(")

        elif result_code == '00':
            if queryType == NielsenQueryType.INFO:
                data = xml_tree.find("data/data/record")
                # convert to dict
                result = {e.tag: e.text for e in data}
            elif queryType == NielsenQueryType.IMAGE:
                result = xml_tree.find("data").text

            print(result)
            return result

    except Exception as ex:
        print(f"{isbn} xml parsing error")
        print(ex)


def save_image(isbn, data):
    im = Image.open(BytesIO(base64.b64decode(data)))
    im.save(f'{os.getcwd()}\images\{isbn}.png', 'PNG')


# --------------------------------------------------------------------------------------------------------------------


print("Adding a tightly coupled selection of ISBNs to db via api, to test that relationships are established correctly")
print("Connecting")
print(httpx.get(settings.WRIVETED_API + "/version").json())

# chronicles of narnia #1 (two different editions, both isbn13)
narnia1 = ['9780006716631', '9780812424324']
# chronicles of narnia #2 (one edition but with two instances; isbn10 and isbn13)
narnia2 = ['0006716644', '9780006716648']
isbns = narnia1 + narnia2

book_data_for_api = []

for isbn in isbns:

    # skip processing if work exists in db
    response = httpx.get(
        f"{settings.WRIVETED_API}/edition/{isbn}",
        headers={
            "Authorization": f"Bearer {settings.WRIVETED_API_TOKEN}"
        }
    )
    if response.status_code != 404:
        print(f"{isbn} already in db. Skipping...")
        continue

    print(f"{isbn} not in db. Performing Nielsen lookup...")

    book = nielsen_query(isbn, NielsenQueryType.INFO)
    image = nielsen_query(isbn, NielsenQueryType.IMAGE)

    authors = []
    illustrators = []
    genres = []

    # nielsen's max number of outputs for a given type is 10
    for i in range(1, 10):

        # look for "contributors" (authors/illustrators)
        if f"CNF{i}" in book:
            # http://www.onix-codelists.io/codelist/17
            if book[f"CR{i}"] in ["A01", "A02"]:
                authors.append({
                    # removing periods helps eliminate a common issue:
                    # C. S. Lewis & C S Lewis can both come from the same info source,
                    # Hunter S. Thompson & Hunter S Thompson, etc.
                    "last_name": book[f"ICKN{i}"].replace('.',''),
                    "full_name": book[f"CNF{i}"].replace('.','')
                })
            elif book[f"CR{i}"] in ["A12", "A35"]:
                illustrators.append({
                    "full_name": book[f"CNF{i}"]
                })

        # look for genres
        if f"BISACC{i}" in book:
            genres.append({                    
                "bisac_code": book[f"BISACC{i}"],
                "name": book[f"BISACT{i}"]
            }) 

    # short summary good for landbot, long summary good for generating hues
    short_summary = book.get("AUSFSD")
    long_summary = book.get("AUSFLD") 

    # keywords maybe also good for generating hues
    keywords = book.get("KEYWORDS")

    # other useful things
    interest_age = book.get("IA")
    reading_age = book.get("RA")
    pages = book.get("PAGNUM")

    edition = {
        "work_title": book.get("TL"),
        "series_title": book.get("SN"),
        "series_number": book.get("NWS"),
        "title": book.get("TL"),
        "ISBN": book.get("ISBN13"),
        # "cover_url": None,
        "info": {
            "pages": int(pages),
            # "version": "1.0",
            # "other": {
            # }
        },
        "work_info": {
            "short_summary": short_summary,
            "long_summary": long_summary,
            "keywords": keywords,
            "interest_age": interest_age,
            "reading_age": reading_age,
            "genres": genres
        },
        "authors": authors,
        "illustrators": illustrators
    }

    book_data_for_api.append(edition)


# now post them to api
response = httpx.post(
    f"{settings.WRIVETED_API}/editions",
    headers={
        "Authorization": f"Bearer {settings.WRIVETED_API_TOKEN}"
    },
    json=book_data_for_api,
    timeout=60
)


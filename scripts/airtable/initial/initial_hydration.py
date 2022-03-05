# One-off script to hydrate the initial ~5k books from airtable
from enum import Enum
import httpx
from os import getenv
from xml.etree import ElementTree as ET
import httpx
import isbnlib
from google.cloud import storage

class ApiException(Exception):
    """Raise when an API query doesn't go entirely according to plan"""

class ApiAuthException(ApiException):
    """Raise when an api rejects authorization"""

class ApiRateException(ApiException):
    """Raise when an api rate limit has been exceeded"""

class ApiNoResultsException(ApiException):
    """Raise when an api returns no results for a query"""

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def hydrate():
    
    isbns_to_hydrate: list[str] = ["9780545872454"]

    # ---file method---
    # with open('initial_isbns') as isbn_file:  
    #     for line in isbn_file:
    #         isbns_to_hydrate.append(line.strip())

    # ---api method---
    # isbns_to_hydrate_response = httpx.get(
    #     f"{wriveted_api}/editions/to_hydrate",
    #     headers=admin_headers,
    #     params={"limit": max_daily_calls},
    #     timeout=60,
    # )
    # isbns_to_hydrate_response.raise_for_status()
    # isbns_to_hydrate = test_admin_response.json()

    if(len(isbns_to_hydrate) < 1):
        print("No ISBNs to hydrate today. Exiting...")
        return

    print("Hydrating " + str(len(isbns_to_hydrate)) + " ISBNs...")

    # wriveted = WrivetedService()
    nielsen = NielsenService()

    # we quite literally have all day for hydration. but the api doesn't have all day
    # to wait around performing a monolithic db operation at the end, so to be nice 
    # we're going to batch our hydrated books into more digestible chunks
    max_batch_size = 100
    for chunk in chunks(isbns_to_hydrate, max_batch_size):

        book_batch = []

        for isbn in chunk:
            book_data = nielsen.data_query(isbn)
            book_data.other_isbns = isbnlib.editions(book_data.isbn).remove(book_data.isbn)
            book_batch.append(book_data)

        # wriveted.post_hydrated_batch(book_batch)


class WrivetedService:    

    api = \
        getenv("WRIVETED_API") \
        if getenv("WRIVETED_API") \
        else 'http://localhost:8000/v1'

    admin_token = \
        getenv("WRIVETED_API_TOKEN") \
        if getenv("WRIVETED_API_TOKEN") \
        else "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2NDcwNzI1OTEsImlhdCI6MTY0NjM4MTM5MSwic3ViIjoiV3JpdmV0ZWQ6VXNlci1BY2NvdW50OjEyZDA5Mjg4LWU5MjAtNGFkMS04NmQzLTEyNTdjNGFhZGExMCJ9.PJB6UgS9fliBtyh4Mxaq8rHF6LDDIS9M988iaswyMhQ"

    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    def __init__(self):
        assert self.api
        assert self.admin_token
        assert self.admin_headers
        print("Connecting to Wriveted API...")
        version_response = httpx.get(self.api + "/version")
        version_response.raise_for_status()
        print(version_response.json())
        print("Testing admin status...")
        assert self.is_admin()
        print("Wriveted Service ready.")

        
    def is_admin(self):
        test_admin_response = httpx.get(
            f"{self.api}/auth/me",
            headers=self.admin_headers,
        )
        test_admin_response.raise_for_status()
        account_details = test_admin_response.json()

        is_admin = (
            account_details["account_type"] == "user"
            and account_details["user"]["type"] == "wriveted"
        ) or (
            account_details["account_type"] == "service_account"
            and account_details["service_account"]["type"]
            in {
                "backend",
            }
        )
        return is_admin


    def isbn_exists(self, isbn):    
        response = httpx.get(
            f"{self.api}/edition/{isbn}",
            headers=self.admin_headers,
        )
        return response.status_code != 404
  

class Contributor:
    first_name: str | None      # ICFN
    last_name: str              # ICKN

    def __init__(self, first_name, last_name):
        self.first_name = first_name
        self.last_name = last_name

class Genre:
    class GenreSource(Enum):
        BISAC = "BISAC"
        BIC = "BIC"
        THEMA = "THEMA"
        LOCSH = "LOCSH"

    name: str
    source: GenreSource

    def __init__(self, name, source):
        self.name = name
        self.source = self.GenreSource[source]

class ReadingAbility(Enum):
    SPOT = "Where's Spot"
    CAT_HAT = "Cat in the Hat"
    TREEHOUSE = "The 13-Storey Treehouse"
    CHARLIE_CHOCOLATE = "Charlie and the Chocolate Factory"
    HARRY_POTTER = "Harry Potter and the Philosopher's Stone"

# for posterity and Relevance
class RawNielsen:
    summary_short:  str | None      # AUSFSD
    summary_long:   str | None      # AUSFLD
    bic_qualifiers: list[str]       # BIC2QT
    keywords:       str | None      # KEYWORDS
    cbmctext:       str | None      # CBMCTEXT
    interest_age:   str | None      # IA
    reading_age:    str | None      # RA

class NielsenBookData:
    isbn: str
    other_isbns: list[str]

    leading_article: str | None     # LA
    title: str                      # TL
    series_name: str                # SN
    series_number: int | None       # NWS

    authors: list[Contributor]
    illustrators: list[Contributor]

    genres: list[Genre]             # BISACT, BIC2ST, THEMAST, LOCSH
    pages: int | None               # PAGNUM

    # these are likely calculated
    reading_ability: ReadingAbility | None
    min_age: int | None
    max_age: int | None

    country: str                    # COP
    date_published: str
    recommend_status: str
    raw_nielsen: RawNielsen

    image_flag: bool                # IMAGFLAG

    def __init__(self):
        self.authors = []
        self.illustrators = []
        self.genres = []
        self.raw_nielsen = RawNielsen()
        self.raw_nielsen.bic_qualifiers = []
    

class NielsenService:

    api = \
        getenv("NIELSEN_API") \
        if getenv("NIELSEN_API") \
        else "https://ws.nielsenbookdataonline.com/BDOLRest/RESTwebServices/BDOLrequest"

    client_id = \
        getenv("NIELSEN_CLIENT_ID") \
        if getenv("NIELSEN_CLIENT_ID") \
        else "WrivetedWebServices"

    client_password = \
        getenv("NIELSEN_CLIENT_PASSWORD") \
        if getenv("NIELSEN_CLIENT_PASSWORD") \
        else "Wriveted5196"

    max_daily_calls = \
        int(getenv("MAX_NIELSEN_CALLS")) \
        if getenv("MAX_NIELSEN_CALLS") \
        else 10_000

    boring_bic2st_list = [
        "Educational English language Readers and reading schemes",
        "Educational English language and Literacy Schemes",
        "Educational Food Technology",
        "Educational Mathematics and numeracy",
        "Educational Languages other than english",
        "Teaching of specific groups and persons"
    ]

    boring_prodct_list = [
        "school text books and study guides",
        "reference and home learning",
        "Education and teaching",
        "Encyclopaedia and general reference",
        "Science and mathematics textbooks"
    ]

    def __init__(self):
        assert self.api
        assert self.client_id
        assert self.client_password
        assert self.max_daily_calls
        print("Connecting to Nielsen API...")
        assert self.data_query('9781449355739')
        print("Nielsen Service ready.")
    

    def data_query(self, isbn: str) -> NielsenBookData:
        response: httpx.Response = httpx.get(
            self.api,
            params={
                "clientId": self.client_id,
                "password": self.client_password,
                "from": 0,
                "to": 1,
                "indexType": 0,
                "format": 7,
                "resultView": 2,
                "field0": 1,
                "value0": isbn,
            },
        )
        raw_response_content = (
            '<?xml version="1.0" encoding="ISO-8859-1"?>'
            + response.content.decode("UTF-8").replace(
                '<?xml version="1.0" encoding="ISO-8859-1"?>', ""
            )
        )
        xml_tree = ET.fromstring(raw_response_content)

        try:
            result_code = xml_tree.find("resultCode").text
            hits = xml_tree.find("hits").text
            self.check_result(isbn, result_code, hits)            

            data = xml_tree.find("data/data/record")
            # convert to dict
            result = {e.tag: e.text for e in data}

            # start populating the output object
            output = NielsenBookData()

            # get the basics out of the way
            output.isbn = result.get("ISBN13")
            output.leading_article = result.get("LA")
            output.title = result.get("TL")
            output.series_name = result.get("SN")
            output.series_number = int(result.get("NWS")) if result.get("NWS") else None
            output.pages = result.get("PAGNUM")    

            # nielsen's max number of outputs for a given type is 10
            # iterate through all such multi-field outputs
            for i in range(1, 10):

                # look for "contributors" (authors/illustrators)
                if f"CNF{i}" in result:
                    # http://www.onix-codelists.io/codelist/17
                    if result.get(f"CR{i}") in ["A01", "A02"]:
                        output.authors.append(Contributor(result.get(f"ICFN{i}"), result.get(f"ICKN{i}")))
                    elif result.get(f"CR{i}") in ["A12", "A35"]:
                        output.illustrators.append(Contributor(result.get(f"ICFN{i}"), result.get(f"ICKN{i}")))

                # look for genres
                if f"BISACT{i}" in result:
                    output.genres.append(Genre(result.get(f"BISACT{i}"), "BISAC"))
                if f"BIC2ST{i}" in result:
                    genre = result.get(f"BIC2ST{i}")
                    # do not recommend BORING books, based on certain BIC genres
                    if any(substring.lower() in genre.lower() for substring in self.boring_bic2st_list): 
                        output.recommend_status = "BORING_OR_REFERENCE"
                    output.genres.append(Genre(result.get(f"BIC2ST{i}"), "BIC"))
                if f"THEMAST{i}" in result:
                    output.genres.append(Genre(result.get(f"THEMAST{i}"), "THEMA"))
                if f"LOCSH{i}" in result:
                    output.genres.append(Genre(result.get(f"LOCSH{i}"), "LOCSH"))

                # look for BIC qualifier(s) (kind of misc. but often useful for age)
                if f"BIC2QT{i}" in result:
                    output.raw_nielsen.bic_qualifiers.append(result.get(f"BIC2QT{i}"))

            prodct = result.get("PRODCT")
            if any(substring.lower() in prodct.lower() for substring in self.boring_prodct_list): 
                output.recommend_status = "BORING_OR_REFERENCE"

            output.raw_nielsen.cbmctext = result.get("CBMCTEXT")

            # short summary good for landbot, long summary good for generating hues
            output.raw_nielsen.summary_short = result.get("AUSFSD")
            output.raw_nielsen.summary_long = result.get("AUSFLD")

            # keywords maybe also good for generating hues
            output.raw_nielsen.keywords = result.get("KEYWORDS")

            # other useful things
            output.raw_nielsen.interest_age = result.get("IA")
            output.raw_nielsen.reading_age = result.get("RA")

            # calculate min and max age
            # break down CBMCTEXT for the integers (make sure to ignore those with 'months' i.e. 0-36 months)
            # if no cbmctext or no useful data do the same with BIC2QT
            # then IA
            # then RA

            # calculate reading ability
            # https://docs.google.com/document/d/1jE6d4U2C0vSyRl6_nCEvGYyauDzyq_xEV8rzFlvuFmY

            output.image_flag = result.get("IMAGFLAG") == "Y"

            return output

        except Exception as ex:
            print(f"{isbn} xml parsing error")
            print(ex)

    
    def image_query(self, isbn: str):
        response: httpx.Response = httpx.get(
            self.api,
            params={
                "clientId": self.client_id,
                "password": self.client_password,
                "from": 0,
                "to": 1,
                "indexType": 2,
                "format": 7,
                "resultView": 2,
                "field0": 1,
                "value0": isbn,
            },
        )
        raw_response_content = response.content.decode("UTF-8")
        xml_tree = ET.fromstring(raw_response_content)

        try:
            result_code = xml_tree.find("resultCode").text
            hits = xml_tree.find("hits").text
            self.check_result(isbn, result_code, hits) 
            result = xml_tree.find("data").text

            print(result)
            return result

        except Exception as ex:
            print(f"{isbn} xml parsing error")
            print(ex)

    
    def check_result(self, isbn, result_code, hits):
        if result_code == "02":
            raise ApiAuthException("Nielsen API rejected the credentials.")

        elif result_code == "50":
            raise ApiRateException("Nielsen rate limit reached.")

        elif result_code == "00":
            if int(hits) < 1:
                raise ApiNoResultsException(f"No results found for isbn {isbn} on Nielsen")
        
        else:
            raise ApiException("Something went wrong when querying Nielsen with the isbn " + isbn)


class GcpStorageService:
    
    credentials = \
        getenv("GOOGLE_APPLICATION_CREDENTIALS") \
        if getenv("GOOGLE_APPLICATION_CREDENTIALS") \
        else "wriveted-cover-images"

    bucket_name = \
        getenv("GCP_IMAGE_BUCKET") \
        if getenv("GCP_IMAGE_BUCKET") \
        else "wriveted-cover-images"

    def __init__(self):
        assert self.credentials
        assert self.bucket_name
        print("Google Cloud Storage Service ready.")

    def upload_cover_image(self, base64_data: str, folder: str, isbn: str):
        # get the filetype from the image string by relying on base64 "magic numbers",
        # defaulting to jpeg
        filetype = {
            '/': "jpg",
            'i': "png",
            'R': "gif",
            'U': "webp"
        }.get(base64_data[0], "jpg")

        client = storage.Client()
        bucket = client.get_bucket(self.bucket_name)
        blob = bucket.blob(f'{folder}/{isbn}.{filetype}')
        blob.upload_from_string(base64_data, content_type=f"image/{filetype}")



if __name__ == "__main__":
    hydrate()
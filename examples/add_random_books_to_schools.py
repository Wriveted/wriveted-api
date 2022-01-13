import csv
import random

import httpx
from pydantic import AnyHttpUrl

from examples.config import settings

print("Script to add a selection of books to the collections of a selection of australian schools")
print("Connecting")
print(httpx.get(settings.WRIVETED_API + "/version").json())

token = settings.WRIVETED_API_TOKEN

book_data = []

with open("Wriveted-books.csv", newline='') as csv_file:
    reader = csv.reader(csv_file)

    # Eat the header line
    headers = next(reader)

    # first_row = next(reader)
    # for i, (h, ex) in enumerate(zip(headers, first_row)):
    #     print(i, h.strip(), "====> ", ex)

    print()

    for i, book_row in enumerate(reader):
        authors = []
        if len(book_row[1]) > 1:
            authors.append(
                {
                    "last_name": book_row[1].split()[-1],
                    "full_name": book_row[1],
                })

        cover_url = None
        if len(book_row[17]) > 1 and book_row[17].startswith("http"):
            cover_url = book_row[17]

        for ISBN in book_row[28].split(','):
            ISBN = ISBN.strip()
            if len(ISBN) > 0:
                new_edition_data = {
                    # "work_title": "string",

                    "title": book_row[0].strip(),
                    "ISBN": ISBN,
                    "cover_url": cover_url,
                    "info": {
                        "Genre": book_row[20],
                        "Illustration Style": book_row[18],
                        "AirTableDump": book_row
                    },
                    "authors": authors,
                    "illustrators": [
                        # {
                        #     "full_name": "string",
                        #     "info": "string"
                        # }
                    ]
                }
                if book_row[80] is not None and len(book_row[80]) > 1:
                    # Add the series title
                    try:
                        (series_title, *_ ) = book_row[80].split(';')
                        new_edition_data['series_title'] = series_title.strip()
                    except ValueError:
                        print("Not adding this series - row was ", book_row[80])


                book_data.append(
                    new_edition_data
                )

schools_response = httpx.get(
    settings.WRIVETED_API + "/schools",
    headers={
        "Authorization": f"Bearer {token}"
    },
    params={
    'limit': 10
})
schools_response.raise_for_status()
schools = schools_response.json()

for school in schools:
    collection_data = random.choices(book_data, k=100)

    if False:
        print("Updating school by setting entire collection", school['name'])
        print(
            httpx.post(
                f"{settings.WRIVETED_API}/school/{school['country_code']}/{school['official_identifier']}/collection",
                json=collection_data,
                timeout=60,
                headers={
                    "Authorization": f"Bearer {token}"
                },
            ).json()
        )
    else:
        print("Updating school with collection changes", school['name'])

        collection_changes = [
            {
                "action": "add",
                "ISBN": d['ISBN'],
                "edition_info": d,
                "copies_on_loan": 0,
                "copies_available": 1,
            } for d in collection_data]
        res = httpx.put(
            f"{settings.WRIVETED_API}/school/{school['country_code']}/{school['official_identifier']}/collection",
            json=collection_changes, timeout=60, headers={"Authorization": f"Bearer {token}"}, )
        res.raise_for_status()
        print(res.json())
    #raise SystemExit
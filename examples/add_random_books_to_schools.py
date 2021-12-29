import csv
import random

import httpx
from pydantic import AnyHttpUrl

from examples.config import settings

print("Script to add all australian schools to Wriveted API")
print("Connecting")
print(httpx.get(settings.WRIVETED_API + "/version").json())


# A User Account Token
user_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2NDE0MzAzOTYsImlhdCI6MTY0MDczOTE5Niwic3ViIjoid3JpdmV0ZWQ6dXNlci1hY2NvdW50OmFhNmZiYjZmLWRhM2MtNDRhZi1iOGM4LWYwMTMxZjJiMTQwZiJ9.rlFDPjYumRfuKFSKHeVC2nI2_Y0-pbY0x9ARI2_cX6A"

# A Service Account Token
service_account_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MDM4MTEzMjMsImlhdCI6MTY0MDczOTMyMywic3ViIjoid3JpdmV0ZWQ6c2VydmljZS1hY2NvdW50OjE2ZmI1ZWFmLWNkMzMtNDljZi05MzBlLWQ2MjhiZjhjNjU2OSJ9.Q8eN0IsstZlD7Wehg0diQlvvtyuVjFY1NP1sE2HzuFg"

token = user_token

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

            new_edition_data = {
                # "work_title": "string",

                "title": book_row[0].strip(),
                "ISBN": ISBN.strip(),
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
    print("Updating school", school['name'])
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
    #raise SystemExit
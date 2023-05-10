import csv

import httpx
from pydantic import AnyHttpUrl

from examples.config import settings

print("Script to add all australian schools to Wriveted API")
print("Connecting")
print(httpx.get(settings.WRIVETED_API + "/version").json())

book_data = []
api_token = settings.WRIVETED_API_TOKEN

with open("Wriveted-books.csv", newline="") as csv_file:
    reader = csv.reader(csv_file)

    # Eat the header line
    headers = next(reader)

    for i in range(1000):
        next(reader)
    # first_row = next(reader)
    # for i, (h, ex) in enumerate(zip(headers, first_row)):
    #     print(i, h.strip(), "====> ", ex)

    print()

    for i, book_row in enumerate(reader):
        authors = []
        if len(book_row[1]) > 1:
            if ";" in book_row[1]:
                author, _ = book_row[1].split(";")
            else:
                author = book_row[1]
            if "," in author:
                # If there is a comma it is likely the last name is first
                last_name, _ = author.split(",")
            else:
                # Otherwise grab the last word
                last_name = author.split()[-1]
            authors.append(
                {
                    "last_name": last_name,
                    "full_name": author,
                    "info": {"raw": book_row[1]},
                }
            )

        cover_url = None
        if len(book_row[17]) > 1 and book_row[17].startswith("http"):
            cover_url = book_row[17]

        for ISBN in book_row[28].split(","):
            new_edition_data = {
                # "work_title": "string",
                "title": book_row[0].strip(),
                "ISBN": ISBN.strip(),
                "cover_url": cover_url,
                "info": {
                    "Genre": book_row[20],
                    "Illustration Style": book_row[18],
                    "AirTableDump": book_row,
                },
                "authors": authors,
                "illustrators": [
                    # {
                    #     "full_name": "string",
                    #     "info": "string"
                    # }
                ],
            }
            if book_row[80] is not None and len(book_row[80]) > 1:
                # Add the series title
                try:
                    (series_title, *_) = book_row[80].split(";")
                    new_edition_data["series"] = {"title": series_title.strip()}

                except ValueError:
                    print("Not adding this series - row was ", book_row[80])

            # print(
            #     httpx.post(
            #         settings.WRIVETED_API + "/edition",
            #         json=new_edition_data
            #    ).json()
            # )

            book_data.append(new_edition_data)

        if i >= 100 and i % 100 == 0:
            response = httpx.post(
                settings.WRIVETED_API + "/editions",
                json=book_data,
                headers={"Authorization": f"Bearer {api_token}"},
                timeout=60,
            )
            response.raise_for_status()
            print(response.json())
            book_data = []

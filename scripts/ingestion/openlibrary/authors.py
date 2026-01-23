import csv
import ctypes as ct

import pydantic_core
from more_itertools import chunked
from rich import print
from sqlalchemy.orm import Session

from app import crud
from app.config import get_settings
from app.db.session import database_connection
from app.schemas.author import AuthorCreateIn

GCP_PROJECT_ID: str = "wriveted-api"
GCP_LOCATION: str = "us-central1"

settings = get_settings()

engine, SessionLocal = database_connection(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
)


def open_library_author_to_wriveted_author(author_data: dict) -> AuthorCreateIn:
    full_name = author_data.get("name", "")
    if full_name:
        *first_name, last_name = full_name.split(" ")
        first_name = " ".join(first_name)
    else:
        first_name = ""
        last_name = ""
    return AuthorCreateIn(
        first_name=first_name,
        last_name=last_name,
        info={
            "external-ids": [
                {
                    "type": "openlibrary",
                    "key": author_data.get("key"),
                }
            ]
        },
    )


filename = "/home/brian/data/openlibrary/ol_dump_authors_2024-04-30.txt"


# See https://stackoverflow.com/a/54517228 for more info on this
csv.field_size_limit(int(ct.c_ulong(-1).value // 2))

with Session(engine) as session:
    with open(filename, "r") as csv_in:
        csvreader = csv.reader(csv_in, delimiter="\t")

        for i, row_batch_batch in enumerate(chunked(csvreader, 10_000)):
            author_data = []

            for row in row_batch_batch:
                if len(row) > 4:
                    json_data = row[4]
                    author_data.append(pydantic_core.from_json(json_data))

            author_create_instances = [
                open_library_author_to_wriveted_author(author) for author in author_data
            ]

            res = crud.author.create_in_bulk(
                session, bulk_author_data_in=author_create_instances
            )
            print(i, "committing")
            session.commit()

    print("Done")
    #
    # author_create_instances = [
    #     open_library_author_to_wriveted_author(author)
    #     for author in author_data
    # ]
    #
    # res = crud.author.create_in_bulk(
    #     session,
    #     bulk_author_data_in=author_create_instances
    # )
    #
    # print("committing")
    # session.commit()
    # print("Done")
    #

"""
This script hydrates all the books matching some criteria.
"""
import os.path
from typing import List

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import database_connection
from app.models import Collection, Work

settings = get_settings()
api_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2ODI2NDU5OTcsImlhdCI6MTY4MTk1NDc5Nywic3ViIjoiV3JpdmV0ZWQ6VXNlci1BY2NvdW50OmUyNWI3MTE2LTZkZTktNDE5MS1hZjMxLTI1MzQzM2E3YTYzOCJ9.OnxWiSsObEH8xBaDS9WknB3rHWc0C2wyZtuEKrtT3ew"
api = "http://localhost:8000/v1"
#
# wriveted_api_response = httpx.get(
#     f"{api}/version",
#     headers={"Authorization": f"Bearer {api_token}"},
#     timeout=20,
# )
#
# wriveted_api_response.raise_for_status()
# print(f"Connected to wriveted api: {api}")

engine, SessionLocal = database_connection(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
)


def main():
    # Get the works from the special collection
    print("Getting works")
    collection_id = "2cfdfd7d-2d50-42b3-a709-42ee000a98f3"

    with Session(engine) as session:
        collection = session.scalar(
            select(Collection).where(Collection.id == collection_id)
        )
        print(collection)
        isbns_to_hydrate = []
        for item in collection.items[:10]:
            # We only need to hydrate for works that don't have a labelset
            # or don't have an age set.
            if item.work is None or (
                item.work.labelset is None or item.work.labelset.age_origin is None
            ):
                isbn = item.edition_isbn or item.work.editions[0].isbn
                if isbn is not None:
                    isbns_to_hydrate.append(isbn)
            else:
                continue

        print(f"Found {len(isbns_to_hydrate)} works to hydrate")
        print(isbns_to_hydrate)
        wriveted_api_response = httpx.post(
            f"{api}/hydrate",
            headers={"Authorization": f"Bearer {api_token}"},
            json=isbns_to_hydrate,
            timeout=60,
        )

        wriveted_api_response.raise_for_status()


if __name__ == "__main__":
    main()

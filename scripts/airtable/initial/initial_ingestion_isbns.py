# One-off script to ingest the initial ~5k books from airtable, creating unhydrated editions

import os
import httpx
from examples.config import settings

admin_token = settings.WRIVETED_API_TOKEN
admin_headers = {"Authorization": f"Bearer {admin_token}"}

test_admin_response = httpx.get(
    f"{settings.WRIVETED_API}/auth/me",
    headers=admin_headers,
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

assert is_admin  

isbns: list[str] = []  

here = os.path.dirname(os.path.abspath(__file__))
filename = os.path.join(here, 'initial_isbns.txt')
with open(filename) as isbn_file:  
    for line in isbn_file:
        isbns.append({"isbn": line.strip()})

print(
    f"Adding the {len(isbns)} unhydrated airtable books to db"
)
add_books_response = httpx.post(
    settings.WRIVETED_API + "/editions",
    json=isbns,
    timeout=30,
    headers=admin_headers,
)
add_books_response.raise_for_status()
print(add_books_response.json())

print("Done.")
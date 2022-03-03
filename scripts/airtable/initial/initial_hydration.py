# One-off script to hydrate the initial ~5k books from airtable.
# In practice this script will attempt to hydrate all the books in the database.

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
with open('initial_isbns') as isbn_file:  
    for line in isbn_file:
        isbns.append(line.strip())

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
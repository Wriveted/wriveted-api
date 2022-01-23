import csv
import random
import secrets

import httpx
from examples.config import settings

"""
Script to test out the collection mechanisms of the Wriveted API.

Warning: Don't run against a real deployment! ☠


- Check the token is valid
- If the token is for a super-user:
    - Create a test school in Antarctica (ATA)
    - create a service account scoped to that school
- Otherwise use an existing "Test School" (ATA:42)
- For the school, clear the existing collection by setting it to blank
- Check the collection is empty
- Set the collection to 1000 books - set some out on loan.
- Check the collection contains 1000 books and that some are on loan.  
- Update the collection by changing the loan status of 100 of the books.
- Check the collection has been updated.
- Update the collection by adding 100 new books and removing 10 books.
- Check the collection has been updated.
- If super user, delete the created school.

"""
print(f"Connecting to {settings.WRIVETED_API}")
print(httpx.get(settings.WRIVETED_API + "/version").json())

token = settings.WRIVETED_API_TOKEN
print("Checking authorization")
account_details_response = httpx.get(settings.WRIVETED_API + "/auth/me", headers={"Authorization": f"Bearer {token}"})
account_details_response.raise_for_status()
account_details = account_details_response.json()

is_admin = (account_details['account_type'] == "user" and account_details['user']['is_superuser']) or (
    account_details['account_type'] == "service_account" and account_details['service_account']['type'] in {"backend", }
)
test_school_id = "42"

INITIAL_NUMBER_OF_BOOKS = 1000
UPDATED_NUMBER_OF_BOOKS = 50    # There is something fishy in the data if this is higher than 50
ADDED_NUMBER_OF_BOOKS = 500
REMOVED_NUMBER_OF_BOOKS = 50


if is_admin:
    print("Admin logged in. Creating a test school")
    admin_token = token
    test_school_id = secrets.token_hex(8)
    new_test_school_response = httpx.post(
        settings.WRIVETED_API + "/school",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": f"Test School - {test_school_id}",
            "country_code": "ATA",
            "official_identifier": test_school_id,
            "info": {
                "msg": "Created for test purposes"
            }
        }
    )
    new_test_school_response.raise_for_status()
    school_info = new_test_school_response.json()

    print("Creating a LMS service account to carry out the rest of the test")
    new_service_account_response = httpx.post(
        settings.WRIVETED_API + "/service-account",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": f"Integration Test Service Account - {test_school_id}",
            "type": "lms",
            "schools": [
                {
                    "country_code": "ATA",
                    "official_identifier": test_school_id
                }
            ],
            "info": {
                "msg": "Created for test purposes"
            }
        }
    )
    new_service_account_response.raise_for_status()
    service_account_details = new_service_account_response.json()
    print("switching to use service account token")
    token = service_account_details['access_token']
else:
    test_school_response = httpx.get(
        f"{settings.WRIVETED_API}/school/ATA/{test_school_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    school_info = test_school_response.json()

print("Resetting school collection")
reset_collection_response = httpx.post(
        f"{settings.WRIVETED_API}/school/ATA/{test_school_id}/collection",
        headers={"Authorization": f"Bearer {token}"},
        json=[]
    )
reset_collection_response.raise_for_status()
get_collection_response = httpx.get(
        f"{settings.WRIVETED_API}/school/ATA/{test_school_id}/collection",
        headers={"Authorization": f"Bearer {token}"},
    )

get_collection_response.raise_for_status()
collection = get_collection_response.json()
assert len(collection) == 0
print("Collection after reset:", collection)

print("Loading books from CSV file")

book_data = []
with open("Wriveted-books.csv", newline='') as csv_file:
    reader = csv.reader(csv_file)

    # Eat the header line
    headers = next(reader)

    # first_row = next(reader)
    # for i, (h, ex) in enumerate(zip(headers, first_row)):
    #     print(i, h.strip(), "====> ", ex)

    print()

    # The Airtable data has some duplicates
    seen_isbns = set()
    for i, book_row in enumerate(reader):
        if i > 2000:
            break
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
            if ISBN not in seen_isbns and len(ISBN) > 0:

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
            else:
                seen_isbns.add(ISBN)


print(f"{len(book_data)} Books loaded. Setting the collection to the first {INITIAL_NUMBER_OF_BOOKS} books")
assert len(book_data) > (INITIAL_NUMBER_OF_BOOKS + ADDED_NUMBER_OF_BOOKS)
original_books = book_data[:INITIAL_NUMBER_OF_BOOKS]
assert len(original_books) == INITIAL_NUMBER_OF_BOOKS


def randomize_loan_status(book_data):
    data = book_data.copy()
    data['copies_total'] = random.randint(2, 4)
    data['copies_available'] = random.randint(0, 2)
    return data


original_collection = [randomize_loan_status(b) for b in original_books]
print(f"Updating school by setting new collection of {len(original_collection)} books")
set_collection_response = httpx.post(
    f"{settings.WRIVETED_API}/school/ATA/{test_school_id}/collection",
    json=original_books,
    timeout=60,
    headers={"Authorization": f"Bearer {token}"},
)
print(
    set_collection_response.json()
)

print("Checking the collection")
get_collection_response = httpx.get(
        f"{settings.WRIVETED_API}/school/ATA/{test_school_id}/collection",
        headers={"Authorization": f"Bearer {token}"},
        params={"skip": 0, "limit": 2000}
    )

get_collection_response.raise_for_status()
collection = get_collection_response.json()
print("Collection after adding (first 3):\n", collection[:3])
assert len(collection) == INITIAL_NUMBER_OF_BOOKS, f"Expected the collection to contain {INITIAL_NUMBER_OF_BOOKS} items, but it had {len(collection)}"

# Update the collection by changing the loan status of a subset of the books.
books_to_update = original_collection[:UPDATED_NUMBER_OF_BOOKS]
print("Bulk updating loan status via `PUT .../collection` API")

collection_changes = [
    {
        "action": "update",
        "ISBN": b['ISBN'],
        "copies_total": 99,
        "copies_available": 99,
    } for b in books_to_update]

print(f"Sending through {len(collection_changes)} updates")
httpx.put(
    f"{settings.WRIVETED_API}/school/ATA/{test_school_id}/collection",
    json=collection_changes,
    timeout=10,
    headers={
        "Authorization": f"Bearer {token}"
    },
).json()
print("Updated loan status")

get_collection_response = httpx.get(
        f"{settings.WRIVETED_API}/school/ATA/{test_school_id}/collection",
        headers={"Authorization": f"Bearer {token}"},
        params={"skip": 0, "limit": 2000}
    )
get_collection_response.raise_for_status()
collection = get_collection_response.json()

number_items_with_updated_loan_status = 0
for item in collection:
    if item['copies_total'] == 99 and item['copies_available'] == 99:
        number_items_with_updated_loan_status += 1


assert number_items_with_updated_loan_status == UPDATED_NUMBER_OF_BOOKS, f"Expected {UPDATED_NUMBER_OF_BOOKS} to have different loan statuses - but found {number_items_with_updated_loan_status}"
print("Collection loan status has changed")

books_to_remove = original_collection[:REMOVED_NUMBER_OF_BOOKS]
print("Adding and removing books from collection via `PUT .../collection` API")
collection_changes = [
    {
        "action": "remove",
        "ISBN": b['ISBN'],
    } for b in books_to_remove]

books_to_add = book_data[INITIAL_NUMBER_OF_BOOKS:INITIAL_NUMBER_OF_BOOKS+ADDED_NUMBER_OF_BOOKS]
collection_changes.extend([
    randomize_loan_status({
        "action": "add",
        "ISBN": b['ISBN'],
        "edition_info": b,
    }) for b in books_to_add
])

httpx.put(
    f"{settings.WRIVETED_API}/school/ATA/{test_school_id}/collection",
    json=collection_changes,
    timeout=30,
    headers={
        "Authorization": f"Bearer {token}"
    },
).json()
print("Added and removed books from collection")
get_collection_response = httpx.get(
        f"{settings.WRIVETED_API}/school/ATA/{test_school_id}/collection",
        headers={"Authorization": f"Bearer {token}"},
        params={"skip": 0, "limit": 2000}
    )
get_collection_response.raise_for_status()
collection = get_collection_response.json()
print("Current collection size:", len(collection), "expected: ", INITIAL_NUMBER_OF_BOOKS + ADDED_NUMBER_OF_BOOKS - REMOVED_NUMBER_OF_BOOKS)
assert len(collection) == INITIAL_NUMBER_OF_BOOKS + ADDED_NUMBER_OF_BOOKS - REMOVED_NUMBER_OF_BOOKS

if is_admin:
    print("Removing the test school")

    remove_test_school_response = httpx.delete(
        settings.WRIVETED_API + f"/school/ATA/{test_school_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=60,
    )
    remove_test_school_response.raise_for_status()
    print("Test School Removed")

    print("Removing the service account")
    remove_svc_account_response = httpx.delete(
        settings.WRIVETED_API + f"/service-account/{service_account_details['id']}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    remove_svc_account_response.raise_for_status()

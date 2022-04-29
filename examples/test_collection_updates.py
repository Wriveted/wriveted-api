import csv
import random
import secrets
import time

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
start_time = time.time()
version_response = httpx.get(settings.WRIVETED_API + "/v1/version", timeout=30)
version_response.raise_for_status()
print(version_response.json())

token = settings.WRIVETED_API_TOKEN
print("Checking authorization")
account_details_response = httpx.get(
    settings.WRIVETED_API + "/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
)
account_details_response.raise_for_status()
account_details = account_details_response.json()

is_admin = (
    account_details["account_type"] == "user"
    and account_details["user"]["type"] in {"wriveted"}
) or (
    account_details["account_type"] == "service_account"
    and account_details["service_account"]["type"]
    in {
        "backend",
    }
)
test_school_id = "42"

INITIAL_NUMBER_OF_BOOKS = 15
UPDATED_NUMBER_OF_BOOKS = 10
ADDED_NUMBER_OF_BOOKS = 20
REMOVED_NUMBER_OF_BOOKS = 5


if is_admin:
    print("Admin logged in. Creating a test school")
    admin_token = token
    test_school_id = secrets.token_hex(8)
    new_test_school_response = httpx.post(
        settings.WRIVETED_API + "/v1/school",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": f"Test School - {test_school_id}",
            "country_code": "ATA",
            "official_identifier": test_school_id,
            "info": {"location": {"state": "", "postcode": ""}},
        },
        timeout=120,
    )
    new_test_school_response.raise_for_status()
    school_info = new_test_school_response.json()
    print(school_info)
    school_wriveted_id = school_info["wriveted_identifier"]

    print("Creating a LMS service account to carry out the rest of the test")
    new_service_account_response = httpx.post(
        settings.WRIVETED_API + "/v1/service-account",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": f"Integration Test Service Account - {test_school_id}",
            "type": "lms",
            "schools": [{"wriveted_identifier": school_wriveted_id}],
            "info": {"msg": "Created for test purposes"},
        },
    )

    new_service_account_response.raise_for_status()
    service_account_details = new_service_account_response.json()
    print("switching to use service account token")
    token = service_account_details["access_token"]
else:
    test_school_response = httpx.get(
        f"{settings.WRIVETED_API}/v1/schools",
        params={"country_code": "ATA"},
        headers={"Authorization": f"Bearer {token}"},
    )
    school_info = test_school_response.json()[0]

print("Resetting school collection")
reset_collection_response = httpx.post(
    f"{settings.WRIVETED_API}/v1/school/{school_wriveted_id}/collection",
    headers={"Authorization": f"Bearer {token}"},
    json=[],
)
reset_collection_response.raise_for_status()
get_collection_response = httpx.get(
    f"{settings.WRIVETED_API}/v1/school/{school_wriveted_id}/collection",
    headers={"Authorization": f"Bearer {token}"},
)

get_collection_response.raise_for_status()
collection = get_collection_response.json()
assert len(collection) == 0
print("Collection after reset:", collection)

isbns = [
    "9781743816332",
    "9781922244932",
    "9781925227642",
    "9781743532980",
    "9781922077400",
    "9781841211046",
    "9780143306726",
    "9781743620014",
    "9781905294251",
    "9780141305103",
    "9780746096673",
    "9780207186240",
    "9780152014780",
    "9780545349444",
    "9780908643677",
    "9780733616129",
    "9781526604071",
    "9780207177965",
    "9781845075965",
    "9780670078875",
    "9781865044255",
    "9780734409126",
    "9780192794055",
    "9780207198694",
    "9781925381177",
    "9780732998837",
    "9780241346228",
    "9780416393804",
    "9780140305951",
    "9781742998848",
    "9781927271896",
    "9780734404206",
    "9780143794042",
    "9780099488392",
    "9780086461629",
    "9781742765129",
    "9781406302400",
    "9780207199141",
    "9780992478070",
    "9781865041704",
    "9781925360066",
    "9781863683500",
    "9781760507398",
    "9781921504600",
    "9780340999080",
    "9781921504365",
    "9781597371384",
    "9781760290917",
]

print(
    f"{len(isbns)} loaded. Setting the collection to the first {INITIAL_NUMBER_OF_BOOKS} books"
)
assert len(isbns) > (INITIAL_NUMBER_OF_BOOKS + ADDED_NUMBER_OF_BOOKS)
original_books = isbns[:INITIAL_NUMBER_OF_BOOKS]
assert len(original_books) == INITIAL_NUMBER_OF_BOOKS


def randomize_loan_status(isbn):
    return {
        "isbn": isbn,
        "copies_total": random.randint(2, 4),
        "copies_available": random.randint(2, 4),
    }


original_collection = [randomize_loan_status(b) for b in original_books]
print(f"Updating school by setting new collection of {len(original_collection)} books")
print(original_collection)
set_collection_response = httpx.post(
    f"{settings.WRIVETED_API}/v1/school/{school_wriveted_id}/collection",
    json=original_collection,
    timeout=120,
    headers={"Authorization": f"Bearer {token}"},
)
print(set_collection_response.json())
set_collection_response.raise_for_status()

print("Checking the collection")
get_collection_response = httpx.get(
    f"{settings.WRIVETED_API}/v1/school/{school_wriveted_id}/collection",
    headers={"Authorization": f"Bearer {token}"},
    params={"skip": 0, "limit": 2000},
    timeout=120,
)

get_collection_response.raise_for_status()
collection = get_collection_response.json()
print("Collection after adding (first 3):\n", collection[:3])
assert (
    len(collection) == INITIAL_NUMBER_OF_BOOKS
), f"Expected the collection to contain {INITIAL_NUMBER_OF_BOOKS} items, but it had {len(collection)}"

# Update the collection by changing the loan status of a subset of the books.
books_to_update = original_collection[:UPDATED_NUMBER_OF_BOOKS]
print("Bulk updating loan status via `PUT .../collection` API")
time.sleep(0.5)
collection_changes = [
    {
        "action": "update",
        "isbn": b["isbn"],
        "copies_total": 99,
        "copies_available": 99,
    }
    for b in books_to_update
]

print(f"Sending through {len(collection_changes)} updates")
r = httpx.patch(
    f"{settings.WRIVETED_API}/v1/school/{school_wriveted_id}/collection",
    json=collection_changes,
    timeout=120,
    headers={"Authorization": f"Bearer {token}"},
)
print(r.json())
r.raise_for_status()
print("Updated loan status")

get_collection_response = httpx.get(
    f"{settings.WRIVETED_API}/v1/school/{school_wriveted_id}/collection",
    headers={"Authorization": f"Bearer {token}"},
    params={"skip": 0, "limit": 2000},
    timeout=120,
)
get_collection_response.raise_for_status()
collection = get_collection_response.json()


number_items_with_updated_loan_status = 0
for item in collection:
    if item["copies_total"] == 99 and item["copies_available"] == 99:
        number_items_with_updated_loan_status += 1

assert (
    number_items_with_updated_loan_status == UPDATED_NUMBER_OF_BOOKS
), f"Expected {UPDATED_NUMBER_OF_BOOKS} to have different loan statuses - but found {number_items_with_updated_loan_status}"
print("Collection loan status has changed")

books_to_remove = original_collection[:REMOVED_NUMBER_OF_BOOKS]
print("Adding and removing books from collection via `PUT .../collection` API")
collection_changes = [
    {
        "action": "remove",
        "isbn": b["isbn"],
    }
    for b in books_to_remove
]

books_to_add = isbns[
    INITIAL_NUMBER_OF_BOOKS : INITIAL_NUMBER_OF_BOOKS + ADDED_NUMBER_OF_BOOKS
]
collection_changes.extend(
    [
        {
            "action": "add",
            "isbn": b,
        }
        for b in books_to_add
    ]
)

r = httpx.patch(
    f"{settings.WRIVETED_API}/v1/school/{school_wriveted_id}/collection",
    json=collection_changes,
    timeout=120,
    headers={"Authorization": f"Bearer {token}"},
)
r.raise_for_status()
print(r.json())
print("Added and removed books from collection")
get_collection_response = httpx.get(
    f"{settings.WRIVETED_API}/v1/school/{school_wriveted_id}/collection",
    headers={"Authorization": f"Bearer {token}"},
    params={"skip": 0, "limit": 2000},
    timeout=120,
)
get_collection_response.raise_for_status()
collection = get_collection_response.json()
print(
    "Current collection size:",
    len(collection),
    "expected: ",
    INITIAL_NUMBER_OF_BOOKS + ADDED_NUMBER_OF_BOOKS - REMOVED_NUMBER_OF_BOOKS,
)
assert (
    len(collection)
    == INITIAL_NUMBER_OF_BOOKS + ADDED_NUMBER_OF_BOOKS - REMOVED_NUMBER_OF_BOOKS
)

if is_admin:
    print("Removing the test school")

    remove_test_school_response = httpx.delete(
        f"{settings.WRIVETED_API}/v1/school/{school_wriveted_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=120,
    )
    remove_test_school_response.raise_for_status()
    print("Test School Removed")

    print("Removing the service account")
    remove_svc_account_response = httpx.delete(
        f"{settings.WRIVETED_API}/v1/service-account/{service_account_details['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=120,
    )
    remove_svc_account_response.raise_for_status()

print(f"Processing took: {time.time() - start_time:.2f} seconds")

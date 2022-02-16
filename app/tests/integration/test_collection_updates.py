import pytest
import csv
import random
import secrets
import time

from app.services.editions import get_definitive_isbn


def test_collection_management(client, settings,
                               test_school, service_account_for_test_school, test_school_service_account_headers):
    """
    Test out the collection mechanisms of the Wriveted API.

    """
    start_time = time.time()
    print("Checking authorization")
    account_details_response = client.get("/v1/auth/me", headers=test_school_service_account_headers)
    account_details_response.raise_for_status()
    account_details = account_details_response.json()

    is_admin = (account_details['account_type'] == "user" and account_details['user']['is_superuser']) or (
        account_details['account_type'] == "service_account" and account_details['service_account']['type'] in {"backend", }
    )

    INITIAL_NUMBER_OF_BOOKS = 100
    UPDATED_NUMBER_OF_BOOKS = 50
    ADDED_NUMBER_OF_BOOKS = 50
    REMOVED_NUMBER_OF_BOOKS = 10

    test_school_id = test_school.wriveted_identifier

    print("Resetting school collection")
    reset_collection_response = client.post(
            f"/v1/school/{test_school_id}/collection",
            headers=test_school_service_account_headers,
            json=[]
        )
    reset_collection_response.raise_for_status()
    get_collection_response = client.get(
            f"/v1/school/{test_school_id}/collection",
            headers=test_school_service_account_headers,
        )

    get_collection_response.raise_for_status()
    collection = get_collection_response.json()
    assert len(collection) == 0
    print("Collection after reset:", collection)

    print("Loading books from CSV file")

    book_data = []
    with open("../data/test-books.csv", newline='', encoding='cp437') as csv_file:
        reader = csv.reader(csv_file)

        # Eat the header line
        headers = next(reader)

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
                ISBN = get_definitive_isbn(ISBN.strip().upper())
                if ISBN not in seen_isbns and len(ISBN) > 0:

                    new_edition_data = {
                        # "work_title": "string",

                        "title": book_row[0].strip(),
                        "ISBN": ISBN.strip(),
                        "cover_url": cover_url,
                        "info": {
                            "genre": book_row[20],
                            "pages": 50,
                            "other": {
                                "airtable_dump": '|'.join(book_row)
                            }
                        },
                        "work_info": {
                            # "short_summary": short_summary,
                            # "long_summary": long_summary,
                            # "keywords": keywords,
                            # "interest_age": interest_age,
                            # "reading_age": reading_age,
                            # "genres": genres
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
    set_collection_response = client.post(
        f"/v1/school/{test_school_id}/collection",
        json=original_books,
        timeout=30,
        headers=test_school_service_account_headers,
    )
    print(
        set_collection_response.json()
    )

    print("Checking the collection")
    get_collection_response = client.get(
            f"/v1/school/{test_school_id}/collection",
            headers=test_school_service_account_headers,
            params={"skip": 0, "limit": 2000},
            timeout=30
        )

    get_collection_response.raise_for_status()
    collection = get_collection_response.json()
    print("Collection after adding (first 3):\n", collection[:3])
    assert len(collection) == INITIAL_NUMBER_OF_BOOKS, f"Expected the collection to contain {INITIAL_NUMBER_OF_BOOKS} items, but it had {len(collection)}"

    # Update the collection by changing the loan status of a subset of the books.
    books_to_update = original_collection[:UPDATED_NUMBER_OF_BOOKS]
    print("Bulk updating loan status via `PUT .../collection` API")
    time.sleep(0.5)
    collection_changes = [
        {
            "action": "update",
            "ISBN": b['ISBN'],
            "copies_total": 99,
            "copies_available": 99,
        } for b in books_to_update]

    print(f"Sending through {len(collection_changes)} updates")
    r = client.put(
        f"/v1/school/{test_school_id}/collection",
        json=collection_changes,
        timeout=120,
        headers=test_school_service_account_headers,
    )
    print(r.status_code)
    print(r.json())
    print("Updated loan status")

    get_collection_response = client.get(
            f"/v1/school/{test_school_id}/collection",
            headers=test_school_service_account_headers,
            params={"skip": 0, "limit": 2000},
            timeout=120
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

    client.put(
        f"/v1/school/{test_school_id}/collection",
        json=collection_changes,
        timeout=120,
        headers=test_school_service_account_headers,
    ).json()
    print("Added and removed books from collection")
    get_collection_response = client.get(
            f"/v1/school/{test_school_id}/collection",
            headers=test_school_service_account_headers,
            params={"skip": 0, "limit": 2000},
            timeout=120
        )
    get_collection_response.raise_for_status()
    collection = get_collection_response.json()
    print("Current collection size:", len(collection), "expected: ", INITIAL_NUMBER_OF_BOOKS + ADDED_NUMBER_OF_BOOKS - REMOVED_NUMBER_OF_BOOKS)
    assert len(collection) == INITIAL_NUMBER_OF_BOOKS + ADDED_NUMBER_OF_BOOKS - REMOVED_NUMBER_OF_BOOKS

    print(f"Processing took: {time.time() - start_time:.2f} seconds")

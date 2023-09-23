from app.models.collection_item_activity import CollectionItemReadStatus


def test_collection_item_activity_creation_and_fetching(
    client,
    test_unhydrated_editions,
    test_user_account,
    test_user_account_headers,
    test_public_user_hacker,
    test_public_user_hacker_headers,
):
    test_user_id = str(test_user_account.id)

    print("Creating new user collection")
    user_collection_create_response = client.post(
        "/v1/collection",
        headers=test_user_account_headers,
        json={
            "name": "Test collection",
            "user_id": test_user_id,
        },
    )
    user_collection_create_response.raise_for_status()
    user_collection_create_response_data = user_collection_create_response.json()
    user_collection_id = user_collection_create_response_data["id"]

    user_get_collection_response = client.get(
        f"/v1/collection/{user_collection_id}",
        headers=test_user_account_headers,
    )
    user_get_collection_response.raise_for_status()

    print("Updating user collection")
    items = [
        {"edition_isbn": edition.isbn, "copies_total": 1, "copies_available": 1}
        for edition in test_unhydrated_editions
    ]
    user_collection_update_response = client.put(
        f"/v1/collection/{user_collection_id}/items",
        headers=test_user_account_headers,
        json=items,
    )
    user_collection_update_response.raise_for_status()

    user_get_collection_item_response = client.get(
        f"/v1/collection/{user_collection_id}/items",
        headers=test_user_account_headers,
        params={"limit": 1},
    )
    user_get_collection_item_response.raise_for_status()

    user_collection_item_data = user_get_collection_item_response.json()
    user_collection_item = user_collection_item_data["data"][0]
    collection_item_id = user_collection_item["id"]

    print("Set collection item as being currently read")
    user_collection_item_activity_create_response = client.post(
        "/v1/collection-item-activity",
        headers=test_user_account_headers,
        json={
            "reader_id": test_user_id,
            "collection_item_id": collection_item_id,
            "status": CollectionItemReadStatus.READING,
        },
    )
    user_collection_item_activity_create_response.raise_for_status()

    print("Query for collection items being read")
    collection_items_being_read_response = client.get(
        f"/v1/collection/{user_collection_id}/items",
        headers=test_user_account_headers,
        params={"read_status": "READING"},
    )
    collection_items_being_read_response.raise_for_status()

    collection_items_being_read_data = collection_items_being_read_response.json()
    assert len(collection_items_being_read_data["data"]) == 1
    assert collection_items_being_read_data["data"][0]["id"] == collection_item_id

    print("Query for collection items interacted with by current user")
    collection_items_interacted_with_response = client.get(
        f"/v1/collection/{user_collection_id}/items",
        headers=test_user_account_headers,
        params={"reader_id": test_user_id},
    )
    collection_items_interacted_with_response.raise_for_status()

    collection_items_interacted_with_data = (
        collection_items_interacted_with_response.json()
    )
    assert len(collection_items_interacted_with_data["data"]) == 1
    assert collection_items_interacted_with_data["data"][0]["id"] == collection_item_id

    # Hacker to test permissions

    print("Testing auth/me endpoint for hacker")

    hacker_id = str(test_public_user_hacker.id)

    print("Attempting to create collection item activity for another user")
    hacker_collection_item_activity_create_response = client.post(
        "/v1/collection-item-activity",
        headers=test_public_user_hacker_headers,
        json={
            "reader_id": test_user_id,
            "collection_item_id": collection_item_id,
            "status": CollectionItemReadStatus.READING,
        },
    )
    assert hacker_collection_item_activity_create_response.status_code == 403

    print("Attempting to query for collection items being read by another user")
    hacker_collection_items_being_read_response = client.get(
        f"/v1/collection/{user_collection_id}/items",
        headers=test_public_user_hacker_headers,
        params={"reader_id": test_user_id, "read_status": "READING"},
    )
    assert hacker_collection_items_being_read_response.status_code == 403

    print("Attempting to add activity on a collection item from another user")
    hacker_collection_item_activity_create_response = client.post(
        "/v1/collection-item-activity",
        headers=test_public_user_hacker_headers,
        json={
            "reader_id": hacker_id,
            "collection_item_id": collection_item_id,
            "status": CollectionItemReadStatus.READING,
        },
    )
    assert hacker_collection_item_activity_create_response.status_code == 403

    # Test that user can create a single collection item and activity together

    item_and_activity_create_response = client.post(
        f"/v1/collection/{user_collection_id}/item",
        headers=test_user_account_headers,
        json={
            "title": "Lonely book",
            "author": "Lonely author",
            "read_status": CollectionItemReadStatus.READ,
            "reader_id": test_user_id,
        },
    )
    item_and_activity_create_response.raise_for_status()

    item_and_activity_create_data = item_and_activity_create_response.json()
    new_item_id = item_and_activity_create_data["id"]

    new_item_response = client.get(
        f"/v1/collection-item/{new_item_id}",
        headers=test_user_account_headers,
    )
    new_item_response.raise_for_status()

    activity_fetch_response = client.get(
        f"/v1/collection/{user_collection_id}/items",
        headers=test_user_account_headers,
        params={
            "reader_id": test_user_id,
            "read_status": "READ",
        },
    )
    activity_fetch_response.raise_for_status()

    activity_fetch_data = activity_fetch_response.json()
    assert len(activity_fetch_data["data"]) == 1
    assert activity_fetch_data["data"][0]["id"] == new_item_id

    # Test that hacker can't do the same, for someone else

    hacker_item_and_activity_create_response = client.post(
        f"/v1/collection/{user_collection_id}/item",
        headers=test_public_user_hacker_headers,
        json={
            "title": "Sinister, lonely book (extra controversial edition)",
            "author": "Sinister, lonely author",
            "read_status": CollectionItemReadStatus.READ,
            "reader_id": test_user_id,
        },
    )
    assert hacker_item_and_activity_create_response.status_code == 403

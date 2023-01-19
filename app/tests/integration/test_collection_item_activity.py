from app.models.collection_item_activity import CollectionItemReadStatus


def test_collection_item_activity_creation_and_fetching(
    client,
    test_unhydrated_editions,
    test_user_account,
    test_user_account_headers,
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
        f"/v1/collection-item-activity",
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

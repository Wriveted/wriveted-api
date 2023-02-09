from app import crud


def test_user_collection_rename(
    client,
    session,
    test_user_account,
    test_user_account_headers,
    test_user_empty_collection,
):
    # Test that the user can rename a collection
    patch_collection_response = client.patch(
        f"/v1/collection/{test_user_empty_collection.id}",
        json={
            "name": "new name",
        },
        headers=test_user_account_headers,
    )
    patch_collection_response.raise_for_status()
    collection = crud.collection.get(session, test_user_empty_collection.id)
    session.refresh(collection)
    assert collection.name == "new name"


def test_user_can_update_collection_with_unhydrated_editions(
    client,
    session,
    test_user_account,
    test_user_account_headers,
    test_user_empty_collection,
    test_unhydrated_editions,
):
    # Test that the user can add unhydrated items by isbn to a collection
    patch_collection_response = client.patch(
        f"/v1/collection/{test_user_empty_collection.id}",
        json={
            "items": [
                {
                    "edition_isbn": edition.isbn,
                }
                for edition in test_unhydrated_editions
            ],
        },
        headers=test_user_account_headers,
    )
    patch_collection_response.raise_for_status()
    collection_items = crud.collection.get(session, test_user_empty_collection.id).items
    assert len(collection_items) == len(test_unhydrated_editions)


def test_user_can_remove_collection_items_isbn(
    client, session, test_user_account, test_user_account_headers, test_user_collection
):
    # Test that the user can remove items from a collection by isbn
    patch_collection_response = client.patch(
        f"/v1/collection/{test_user_collection.id}",
        json={
            "items": [
                {"edition_isbn": item.edition_isbn, "action": "remove"}
                for item in test_user_collection.items
            ],
        },
        headers=test_user_account_headers,
    )
    patch_collection_response.raise_for_status()
    collection = crud.collection.get(session, test_user_collection.id)
    session.refresh(collection)
    assert len(collection.items) == 0


def test_user_can_remove_collection_items_id(
    client, session, test_user_account, test_user_account_headers, test_user_collection
):
    # Test that the user can remove items from a collection by ID
    patch_collection_response = client.patch(
        f"/v1/collection/{test_user_collection.id}",
        json={
            "items": [
                {"id": item.id, "action": "remove"}
                for item in test_user_collection.items
            ],
        },
        headers=test_user_account_headers,
    )
    patch_collection_response.raise_for_status()
    collection = crud.collection.get(session, test_user_collection.id)
    session.refresh(collection)
    assert len(collection.items) == 0


def test_user_can_update_collection_items_by_id(
    client, session, test_user_account, test_user_account_headers, test_user_collection
):
    item_count = len(test_user_collection.items)
    # Test that the user can remove items from a collection by ID
    patch_collection_response = client.patch(
        f"/v1/collection/{test_user_collection.id}",
        json={
            "items": [
                {
                    "id": item.id,
                    "action": "update",
                    "info": {"other": {"note": "test notes"}},
                }
                for item in test_user_collection.items
            ],
        },
        headers=test_user_account_headers,
    )
    patch_collection_response.raise_for_status()
    collection = crud.collection.get(session, test_user_collection.id)
    session.refresh(collection)
    assert len(collection.items) == item_count
    for item in collection.items:
        session.refresh(item)
        assert "other" in item.info
        assert "note" in item.info["other"]
        assert item.info["other"]["note"] == "test notes"

import uuid

from starlette import status

from app.models.booklist import ListType


def test_backend_service_account_can_list_booklists_empty(
    client, backend_service_account_headers
):
    response = client.get("v1/lists", headers=backend_service_account_headers)

    assert response.status_code == status.HTTP_200_OK


def test_create_empty_booklist_invalid_data_returns_validation_error(
    client, backend_service_account_headers
):
    response = client.post(
        "v1/lists",
        headers=backend_service_account_headers,
        json={"name": "my almost valid booklist", "type": "an invalid book list type"},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_empty_booklist(client, test_user_account_headers):
    response = client.post(
        "v1/lists",
        headers=test_user_account_headers,
        json={"name": "empty wishes", "type": ListType.PERSONAL},
    )

    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    print(data)
    assert "id" in data

    detail_response = client.get(
        f"v1/lists/{data['id']}", headers=test_user_account_headers
    )

    assert detail_response.status_code == status.HTTP_200_OK
    detail = detail_response.json()

    assert "name" in detail
    assert "empty wishes" == detail["name"]
    assert "id" in detail
    assert detail["id"] == data["id"]
    assert "book_count" in detail
    assert detail["book_count"] == 0
    assert "data" in detail
    works = detail["data"]
    assert len(works) == 0


def test_school_admin_can_create_school_booklist(
    client, admin_of_test_school, test_user_account_headers, works_list
):
    response = client.post(
        "v1/lists",
        headers=test_user_account_headers,
        json={
            "name": "wizard wishes",
            "type": ListType.SCHOOL,
            "items": [
                {"work_id": w.id, "order_id": i} for i, w in enumerate(works_list)
            ],
        },
    )

    assert response.status_code == status.HTTP_200_OK
    detail_response = client.get(
        f"v1/lists/{response.json()['id']}",
        params={"limit": 10},
        headers=test_user_account_headers,
    )

    assert detail_response.status_code == status.HTTP_200_OK
    detail = detail_response.json()
    assert "school" in detail
    assert detail["school"] is not None


def test_user_account_can_create_personal_booklist(
    client, test_user_account_headers, works_list
):
    response = client.post(
        "v1/lists",
        headers=test_user_account_headers,
        json={
            "name": "wizard wishes",
            "type": ListType.PERSONAL,
            "items": [
                {"work_id": w.id, "order_id": i} for i, w in enumerate(works_list)
            ],
        },
    )

    assert response.status_code == status.HTTP_200_OK
    detail_response = client.get(
        f"v1/lists/{response.json()['id']}",
        params={"limit": 10},
        headers=test_user_account_headers,
    )

    assert detail_response.status_code == status.HTTP_200_OK
    detail = detail_response.json()
    assert "user" in detail
    assert detail["user"] is not None


def test_create_booklist(client, backend_service_account_headers, works_list):
    response = client.post(
        "v1/lists",
        headers=backend_service_account_headers,
        json={
            "name": "wizard wishes",
            "type": ListType.OTHER_LIST,
            "items": [
                {"work_id": w.id, "order_id": i} for i, w in enumerate(works_list)
            ],
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "id" in data
    assert "data" not in data

    detail_response = client.get(
        f"v1/lists/{data['id']}",
        params={"limit": 10},
        headers=backend_service_account_headers,
    )

    assert detail_response.status_code == status.HTTP_200_OK
    detail = detail_response.json()

    assert "name" in detail
    assert "wizard wishes" == detail["name"]
    assert "id" in detail
    assert detail["book_count"] == 100
    assert detail["id"] == data["id"]
    assert "data" in detail
    items = detail["data"]
    assert len(items) == 10
    for item in items:
        assert "order_id" in item
        assert "work_id" in item
        assert "work" in item
        assert "title" in item["work"]


def test_anyone_can_create_personal_booklist(
    client, test_user_account_headers, works_list
):
    response = client.post(
        "v1/lists",
        headers=test_user_account_headers,
        json={
            "name": "my absolute must reads",
            "type": ListType.PERSONAL,
            "items": [
                {"work_id": w.id, "order_id": i} for i, w in enumerate(works_list)
            ],
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "id" in data
    assert "data" not in data

    detail_response = client.get(
        f"v1/lists/{data['id']}",
        params={"limit": 10},
        headers=test_user_account_headers,
    )

    assert detail_response.status_code == status.HTTP_200_OK
    detail = detail_response.json()

    assert "name" in detail
    assert detail["name"] == "my absolute must reads"
    assert "id" in detail
    assert detail["book_count"] == 100
    assert detail["id"] == data["id"]
    assert "data" in detail
    items = detail["data"]
    assert len(items) == 10
    for item in items:
        assert "order_id" in item
        assert "work_id" in item
        assert "work" in item
        assert "title" in item["work"]


def test_create_school_booklist_without_positions(
    client, admin_of_test_school_headers, works_list
):
    response = client.post(
        "v1/lists",
        headers=admin_of_test_school_headers,
        json={
            "name": "wizard wishes",
            "type": ListType.SCHOOL,
            "items": [{"work_id": w.id} for w in works_list],
        },
    )

    assert response.status_code == status.HTTP_200_OK, response.text
    booklist_id = response.json()["id"]
    ensure_booklist_order_continuous(
        client, admin_of_test_school_headers, booklist_id=booklist_id
    )


def test_rename_personal_booklist(client, test_user_account_headers, works_list):
    create_booklist_response = client.post(
        "v1/lists",
        headers=test_user_account_headers,
        json={
            "name": "wizard wishes",
            "type": ListType.PERSONAL,
            "items": [
                {"work_id": w.id, "order_id": i} for i, w in enumerate(works_list[:20])
            ],
        },
    )
    booklist_id = create_booklist_response.json()["id"]

    # Now patch it to change the name
    edit_booklist_response = client.patch(
        f"v1/lists/{booklist_id}",
        headers=test_user_account_headers,
        json={"name": "witches wonders"},
    )
    assert edit_booklist_response.status_code == 200
    assert edit_booklist_response.json()["name"] == "witches wonders"


def test_user_cant_rename_huey_booklist(
    client, backend_service_account_headers, test_user_account_headers, works_list
):
    create_booklist_response = client.post(
        "v1/lists",
        headers=backend_service_account_headers,
        json={
            "name": "witches wants",
            "type": ListType.HUEY,
            "items": [
                {"work_id": w.id, "order_id": i} for i, w in enumerate(works_list[:20])
            ],
        },
    )
    booklist_id = create_booklist_response.json()["id"]

    # Now if a normal user tries to patch it to change the name:
    edit_booklist_response = client.patch(
        f"v1/lists/{booklist_id}",
        headers=test_user_account_headers,
        json={"name": "witches wonders"},
    )
    assert edit_booklist_response.status_code == 403


def test_change_booklist_type(client, backend_service_account_headers, works_list):
    create_booklist_response = client.post(
        "v1/lists",
        headers=backend_service_account_headers,
        json={
            "name": "wizard wishes",
            "type": ListType.OTHER_LIST,
            "info": {"description": "I'm the original"},
            "items": [
                {"work_id": w.id, "order_id": i} for i, w in enumerate(works_list[:20])
            ],
        },
    )
    assert create_booklist_response.json()["book_count"] == 20
    booklist_id = create_booklist_response.json()["id"]

    # Now patch it to change the type
    edit_booklist_response = client.patch(
        f"v1/lists/{booklist_id}",
        headers=backend_service_account_headers,
        json={
            "type": ListType.REGION,
            # Note this will replace the info blob entirely:
            "info": {"description": "I'm the replacement"},
        },
    )
    assert edit_booklist_response.status_code == 200
    assert edit_booklist_response.json()["type"] == ListType.REGION

    detail_booklist_response = client.get(
        f"v1/lists/{booklist_id}", headers=backend_service_account_headers
    )
    print(detail_booklist_response.json())
    assert detail_booklist_response.status_code == 200
    assert detail_booklist_response.json()["type"] == ListType.REGION
    assert len(detail_booklist_response.json()["data"]) >= 20
    assert "foo" not in detail_booklist_response.json()["info"]
    assert "replacement" in detail_booklist_response.json()["info"]["description"]


def test_add_items_to_booklist(client, backend_service_account_headers, works_list):
    create_booklist_response = client.post(
        "v1/lists",
        headers=backend_service_account_headers,
        json={
            "name": "wizard wishes",
            "type": ListType.OTHER_LIST,
            "info": {"foo": 42},
            "items": [
                {"work_id": w.id, "order_id": i} for i, w in enumerate(works_list[:20])
            ],
        },
    )
    booklist_id = create_booklist_response.json()["id"]

    # Now patch it to add new items
    edit_booklist_response = client.patch(
        f"v1/lists/{booklist_id}",
        headers=backend_service_account_headers,
        json={
            "items": [
                {"action": "add", "work_id": w.id, "order_id": i}
                for i, w in enumerate(works_list[20:], start=19)
            ]
        },
    )
    assert edit_booklist_response.status_code == 200
    assert edit_booklist_response.json()["book_count"] > 20
    ensure_booklist_order_continuous(
        client, backend_service_account_headers, booklist_id
    )


def test_add_items_without_position_to_booklist(
    client, backend_service_account_headers, works_list
):
    create_booklist_response = client.post(
        "v1/lists",
        headers=backend_service_account_headers,
        json={
            "name": "wizard wishes",
            "type": ListType.OTHER_LIST,
            "info": {"foo": 42},
            "items": [{"work_id": w.id} for w in works_list[:20]],
        },
    )
    booklist_id = create_booklist_response.json()["id"]

    # Now patch it to add new items
    edit_booklist_response = client.patch(
        f"v1/lists/{booklist_id}",
        headers=backend_service_account_headers,
        json={
            "items": [
                {"action": "add", "work_id": w.id, "order_id": i}
                for i, w in enumerate(works_list[20:], start=19)
            ]
        },
    )
    assert edit_booklist_response.status_code == 200
    assert edit_booklist_response.json()["book_count"] > 20
    ensure_booklist_order_continuous(
        client, backend_service_account_headers, booklist_id
    )


def test_remove_missing_items_from_booklist(
    client, backend_service_account_headers, works_list
):
    create_booklist_response = client.post(
        "v1/lists",
        headers=backend_service_account_headers,
        json={
            "name": "wizard wishes",
            "type": ListType.OTHER_LIST,
            "info": {"foo": 42},
            "items": [
                {"work_id": w.id, "order_id": i} for i, w in enumerate(works_list[:10])
            ],
        },
    )
    booklist_id = create_booklist_response.json()["id"]

    # Now patch it to remove items that were never in the book list - should be ignored
    edit_booklist_response = client.patch(
        f"v1/lists/{booklist_id}",
        headers=backend_service_account_headers,
        json={
            "items": [{"action": "remove", "work_id": w.id} for w in works_list[20:]]
        },
    )
    assert edit_booklist_response.status_code == 200
    assert edit_booklist_response.json()["book_count"] == 10
    ensure_booklist_order_continuous(
        client, backend_service_account_headers, booklist_id
    )


def test_admin_can_remove_items_from_personal_booklist(
    client, test_user_account, backend_service_account_headers, works_list
):
    create_booklist_response = client.post(
        "v1/lists",
        headers=backend_service_account_headers,
        json={
            "name": "wizard wishes",
            "type": ListType.PERSONAL,
            "user_id": str(test_user_account.id),
            "info": {"foo": 42},
            "items": [
                {"work_id": w.id, "order_id": i} for i, w in enumerate(works_list[:20])
            ],
        },
    )
    create_booklist_response.raise_for_status()
    booklist_id = create_booklist_response.json()["id"]

    # Now patch it to remove items
    edit_booklist_response = client.patch(
        f"v1/lists/{booklist_id}",
        headers=backend_service_account_headers,
        json={
            "items": [{"action": "remove", "work_id": w.id} for w in works_list[10:20]]
        },
    )
    assert edit_booklist_response.status_code == 200
    assert edit_booklist_response.json()["book_count"] == 10
    ensure_booklist_order_continuous(
        client, backend_service_account_headers, booklist_id
    )


def ensure_booklist_order_continuous(
    client, backend_service_account_headers, booklist_id
):
    # check order is continuous
    detail_booklist_response = client.get(
        f"v1/lists/{booklist_id}", headers=backend_service_account_headers
    )
    detail = detail_booklist_response.json()
    positions = [item["order_id"] for item in detail["data"]]
    assert positions == list(range(len(positions)))

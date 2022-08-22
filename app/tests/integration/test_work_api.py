from starlette import status


def test_backend_service_account_can_list_works(
    client, backend_service_account_headers
):
    response = client.get("v1/works", headers=backend_service_account_headers)
    assert response.status_code == status.HTTP_200_OK


def test_backend_service_account_can_get_detail_on_specific_works(
    client, backend_service_account_headers, works_list
):
    for work in works_list:
        response = client.get(
            f"v1/work/{work.id}", headers=backend_service_account_headers
        )
        assert response.status_code == status.HTTP_200_OK
        work_data = response.json()
        assert work_data


def test_backend_service_account_can_get_edit_detail_on_specific_work(
    client, backend_service_account_headers, works_list
):
    work = works_list[0]
    response = client.patch(
        f"v1/work/{work.id}",
        json={"title": "New Title"},
        headers=backend_service_account_headers,
    )
    work_data = response.json()
    assert work_data["title"] == "New Title"


def test_backend_service_account_can_label_work(
    client, backend_service_account_headers, works_list
):
    work = works_list[0]
    response = client.patch(
        f"v1/work/{work.id}",
        json={
            "labelset": {
                "huey_summary": "Blarg!",
                "summary_origin": "HUMAN",
            }
        },
        headers=backend_service_account_headers,
    )
    work_data = response.json()
    assert work_data["labelset"]["huey_summary"] == "Blarg!"


def test_public_account_not_allowed_to_edit_work(
    client, test_user_account_headers, works_list
):
    work = works_list[0]
    response = client.patch(
        f"v1/work/{work.id}",
        json={"title": "New Title"},
        headers=test_user_account_headers,
    )
    assert response.status_code == 403


def test_student_account_not_allowed_to_edit_work(
    client, test_student_user_account_headers, works_list
):
    work = works_list[0]
    response = client.patch(
        f"v1/work/{work.id}",
        json={"title": "New Title"},
        headers=test_student_user_account_headers,
    )
    assert response.status_code == 403

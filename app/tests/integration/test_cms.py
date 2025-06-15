from starlette import status


def test_backend_service_account_can_list_joke_content(
    client, backend_service_account_headers
):
    response = client.get("v1/content/joke", headers=backend_service_account_headers)
    assert response.status_code == status.HTTP_200_OK


def test_backend_service_account_can_list_question_content(
    client, backend_service_account_headers
):
    response = client.get(
        "v1/content/question", headers=backend_service_account_headers
    )
    assert response.status_code == status.HTTP_200_OK

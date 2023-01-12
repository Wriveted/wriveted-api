from starlette import status


def test_search_author(client, backend_service_account_headers, author_list):
    response = client.get(
        "v1/authors",
        params={"query": author_list[0].last_name},
        headers=backend_service_account_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) >= 1

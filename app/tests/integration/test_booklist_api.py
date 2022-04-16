import uuid

from starlette import status



def test_backend_service_account_can_list_booklists(client, backend_service_account_headers):
    response = client.get(
        "v1/lists", headers=backend_service_account_headers
    )
    assert response.status_code == status.HTTP_200_OK



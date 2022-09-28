from starlette import status


def test_kpi_dash_requires_auth(client):
    response = client.get("v1/dashboard/5")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_kpi_dash_requires_admin_auth(client, test_student_user_account_headers):
    response = client.get("v1/dashboard/5", headers=test_student_user_account_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_get_kpi_dash(client, backend_service_account_headers):
    response = client.get("v1/dashboard/5", headers=backend_service_account_headers)
    assert response.status_code == status.HTTP_200_OK

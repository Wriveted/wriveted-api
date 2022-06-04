from starlette import status

from app import crud
from app.models import Student


def test_invalid_class_code_login_attempt(client):
    response = client.get("v1/auth/class-code", json={})
    assert response.status_code != status.HTTP_200_OK

    response = client.post("v1/auth/class-code", json={})
    assert response.status_code != status.HTTP_200_OK

    response = client.post(
        "v1/auth/class-code",
        json={
            "username": "",
            "class_joining_code": "",
        },
    )
    assert response.status_code != status.HTTP_200_OK


def test_register_student_by_class_code(client, session, test_school, test_class_group):
    print("POST registering student")
    response = client.post(
        "v1/auth/register-student",
        json={
            "first_name": "Test",
            "last_name_initial": "U",
            "school_id": str(test_school.wriveted_identifier),
            "class_joining_code": test_class_group.join_code,
        },
    )
    print("register student response", response.text)
    assert response.status_code == status.HTTP_200_OK
    new_user_data = response.json()

    assert "id" in new_user_data
    assert "name" in new_user_data
    assert new_user_data["name"] == "Test U"

    created_user = crud.user.get_or_404(db=session, id=new_user_data["id"])

    assert isinstance(created_user, Student)
    assert created_user.school_id == test_school.id


def test_register_student_by_class_code_then_login(
    client, session, test_school, test_class_group
):
    response = client.post(
        "v1/auth/register-student",
        json={
            "first_name": "Test",
            "last_name_initial": "U",
            "school_id": str(test_school.wriveted_identifier),
            "class_joining_code": test_class_group.join_code,
        },
    )
    print("register student response", response.text)
    new_user_data = response.json()
    print(new_user_data)
    login_response = client.post(
        "v1/auth/class-code",
        json={
            "username": new_user_data["username"],
            "class_joining_code": test_class_group.join_code,
        },
    )
    assert login_response.status_code == 200
    payload = login_response.json()

    assert "access_token" in payload
    headers = {"Authorization": f"bearer {payload['access_token']}"}
    response = client.get("v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["user"]["username"] == new_user_data["username"]

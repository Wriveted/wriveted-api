from starlette import status

from app import crud
from app.schemas.users.user_update import UserUpdateIn


def test_update_user_type(
    session, client, backend_service_account_headers, test_school, test_class_group
):
    user = crud.user.create(
        db=session,
        obj_in=UserUpdateIn(
            name="testman123",
            email="testemail@site.com",
            first_name="test",
            last_name_initial="m",
        ),
    )

    response = client.get(f"v1/user/{user.id}", headers=backend_service_account_headers)
    assert response.status_code == status.HTTP_200_OK

    json = response.json()
    assert json["type"] == "public"

    # convert to student (but lacking class_id)
    user_type_update = {
        "type": "student",
        "username": "testuser123",
        "school_id": test_school.id,
    }

    failed_update_response = client.patch(
        f"v1/user/{user.id}",
        headers=backend_service_account_headers,
        json=user_type_update,
    )

    assert failed_update_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # now add the class_id, completing the requirements to convert from public to student
    user_type_update["class_group_id"] = str(test_class_group.id)

    successful_update_response = client.patch(
        f"v1/user/{user.id}",
        headers=backend_service_account_headers,
        json=user_type_update,
    )

    assert successful_update_response.status_code == status.HTTP_200_OK
    json = successful_update_response.json()
    assert json["type"] == "student"

    session.delete(user)
    session.commit()

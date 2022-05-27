from starlette import status


def test_get_school_events_as_school_admin(
    client,
    test_school,
    admin_of_test_school_headers,
):

    school_id = test_school.wriveted_identifier

    get_events_response = client.get(
        f"/v1/events",
        params={"school_id": school_id},
        headers=admin_of_test_school_headers,
    )
    get_events_response.raise_for_status()
    events = get_events_response.json()

    assert len(events) >= 0


def test_get_school_events_as_user(
    client, test_school, test_schooladmin_account, test_schooladmin_account_headers
):

    school_id = test_school.wriveted_identifier
    assert test_schooladmin_account.school_id is None

    # Shouldn't be able to filter by the school:
    get_events_response = client.get(
        f"/v1/events",
        params={"school_id": school_id},
        headers=test_schooladmin_account_headers,
    )

    assert get_events_response.status_code == status.HTTP_403_FORBIDDEN

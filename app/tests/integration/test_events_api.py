import time

from starlette import status

from app import crud


def test_filter_school_events_as_wriveted_admin(
    client,
    test_school,
    backend_service_account_headers,
):
    school_id = test_school.wriveted_identifier
    get_events_response = client.get(
        f"/v1/events",
        params={"school_id": school_id},
        headers=backend_service_account_headers,
    )
    get_events_response.raise_for_status()
    events = get_events_response.json()["data"]
    assert len(events) >= 0


def test_events_pagination(
    session,
    client,
    test_school,
    backend_service_account_headers,
):
    school_id = test_school.wriveted_identifier
    for i in range(100):
        crud.event.create(session, title=f"TEST {i}", school=test_school, commit=False)
    session.commit()

    get_events_response = client.get(
        f"/v1/events",
        params={"school_id": school_id, "limit": 100},
        headers=backend_service_account_headers,
    )
    get_events_response.raise_for_status()
    events = get_events_response.json()["data"]

    assert len(events) == 100
    # Note events are returned most recent first, so the first event
    # should be "TEST 99"
    assert events[0]["title"] == "TEST 99"
    expected_events = {f"TEST {i}" for i in range(100)}

    assert all(e["title"] in expected_events for e in events)


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
    events = get_events_response.json()["data"]

    assert len(events) >= 0


def test_cant_get_school_events_as_public(
    client, test_school, test_user_account, test_user_account_headers
):

    school_id = test_school.wriveted_identifier
    assert (
        not hasattr(test_user_account, "school_id")
        or test_user_account.school_id is None
    )

    # Shouldn't be able to filter by the school:
    get_events_response = client.get(
        f"/v1/events",
        params={"school_id": school_id},
        headers=test_user_account_headers,
    )

    assert get_events_response.status_code == status.HTTP_403_FORBIDDEN


def test_post_events_api(
    client,
    backend_service_account_headers,
):
    create_event_response = client.post(
        f"/v1/events",
        json={"title": "TEST EVENT", "description": "test description", 'level': 'normal'},
        headers=backend_service_account_headers,
    )
    create_event_response.raise_for_status()
    assert create_event_response.json()["level"] == "normal"


def test_post_events_api_background_process(
    client,
    session_factory,
    backend_service_account,
    backend_service_account_headers,
):
    create_event_response = client.post(
        f"/v1/events",
        json={"title": "Test", "description": "original description", 'level': 'warning'},
        headers=backend_service_account_headers,
    )
    create_event_response.raise_for_status()
    assert create_event_response.json()["level"] == "warning"

    # Wait a tick, then see if the event was modified
    time.sleep(0.01)
    with session_factory() as session:
        events = [e for e in
                  crud.event.get_all_with_optional_filters(
                      db=session,
                      service_account=backend_service_account,
                      level='warning',
                      query_string='Test')
                  if e.title == 'Test']

        assert len(events) == 1
        event = events[0]
        assert event.description == 'MODIFIED'

import datetime
import time

from starlette import status

from app import crud
from app.tests.util.random_strings import random_lower_string


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
        json={
            "title": "TEST EVENT",
            "description": "test description",
            "level": "normal",
        },
        headers=backend_service_account_headers,
    )
    create_event_response.raise_for_status()
    assert create_event_response.json()["level"] == "normal"


def test_post_events_api_with_specified_user(
    client,
    test_user_account,
    backend_service_account_headers,
    test_public_user_hacker_headers,
):
    # create an event with a specified user (with appropriate permissions)
    create_event_response = client.post(
        f"/v1/events",
        json={
            "title": "TEST EVENT",
            "description": "test description",
            "level": "normal",
            "user_id": str(test_user_account.id),
        },
        headers=backend_service_account_headers,
    )
    create_event_response.raise_for_status()
    create_event_response_data = create_event_response.json()
    assert create_event_response_data["user"]["id"] == str(test_user_account.id)

    # create an event with a specified user (without appropriate permissions)
    create_event_response = client.post(
        f"/v1/events",
        json={
            "title": "TEST EVENT",
            "description": "test description",
            "level": "normal",
            "user_id": str(test_user_account.id),
        },
        headers=test_public_user_hacker_headers,
    )
    assert create_event_response.status_code == status.HTTP_403_FORBIDDEN

    # create an event for a user that doesn't exist
    create_event_response = client.post(
        f"/v1/events",
        json={
            "title": "TEST EVENT",
            "description": "test description",
            "level": "normal",
            "user_id": "00000000-0000-0000-0000-000000000000",
        },
        headers=backend_service_account_headers,
    )
    assert create_event_response.status_code == status.HTTP_404_NOT_FOUND


def test_post_events_api_background_process(
    client,
    session_factory,
    backend_service_account,
    backend_service_account_headers,
):
    create_event_response = client.post(
        f"/v1/events",
        json={
            "title": "Test",
            "description": "original description",
            "level": "warning",
        },
        headers=backend_service_account_headers,
    )
    create_event_response.raise_for_status()
    assert create_event_response.json()["level"] == "warning"

    # Wait a tick, then see if the event was modified
    time.sleep(0.5)
    with session_factory() as session:
        events = [
            e
            for e in crud.event.get_all_with_optional_filters(
                db=session,
                service_account=backend_service_account,
                level="warning",
                query_string=["Test"],
            )
            if e.title == "Test"
        ]

        assert len(events) >= 1
        wasModified = False
        for event in events:
            assert event.level in ["warning", "error"]
            if event.description == "MODIFIED":
                wasModified = True

        assert wasModified


def test_event_query_and_prefix(
    client,
    backend_service_account_headers,
):
    # Create some events
    create_event_response_foo_bar = client.post(
        f"/v1/events",
        json={
            "title": "Foo: Bar",
            "description": "Notice the Title: Subtitle format",
            "level": "normal",
        },
        headers=backend_service_account_headers,
    )
    create_event_response_foo_bar.raise_for_status()

    create_event_response_foo_baz = client.post(
        f"/v1/events",
        json={
            "title": "Foo: Baz",
            "description": "Notice the Title: Subtitle format",
            "level": "normal",
        },
        headers=backend_service_account_headers,
    )
    create_event_response_foo_baz.raise_for_status()

    # Test that we can query for a single string
    get_events_response = client.get(
        f"/v1/events",
        params={"query": "Foo: Bar"},
        headers=backend_service_account_headers,
    )
    get_events_response.raise_for_status()
    events = get_events_response.json()["data"]
    assert len(events) == 1

    # Test that we can query for a list of strings
    get_events_response = client.get(
        f"/v1/events",
        params={"query": ["Foo: Bar", "Foo: Baz"]},
        headers=backend_service_account_headers,
    )
    get_events_response.raise_for_status()
    events = get_events_response.json()["data"]
    assert len(events) == 2

    # Test that we can query for prefix with a single string
    get_events_response = client.get(
        f"/v1/events",
        params={"query": "Foo:", "match_prefix": True},
        headers=backend_service_account_headers,
    )
    get_events_response.raise_for_status()
    events = get_events_response.json()["data"]
    assert len(events) == 2

    # Test that we can query for prefix with a list of strings
    get_events_response = client.get(
        f"/v1/events",
        params={"query": ["Foo:"], "match_prefix": True},
        headers=backend_service_account_headers,
    )
    get_events_response.raise_for_status()
    events = get_events_response.json()["data"]
    assert len(events) == 2


def test_event_api_info_filtering(
    client,
    session,
    backend_service_account_headers,
):
    # Create a few events
    crud.event.create(
        session,
        title=f"test event for filtering by info",
        description="test description",
        level="normal",
        info={"work_id": 1234, "boolean": True},
    )
    crud.event.create(
        session,
        title=f"test event for filtering by info",
        description="test description",
        level="normal",
        info={"work_id": 0, "boolean": False, "missing": "value"},
    )

    # Test that we can get events for a work
    get_events_response = client.get(
        f"/v1/events",
        params={"info_jsonpath_match": "($.work_id == 0)"},
        headers=backend_service_account_headers,
    )
    get_events_response.raise_for_status()
    events = get_events_response.json()["data"]
    assert len(events) >= 1
    for e in events:
        assert e["info"]["work_id"] == 0


def test_event_api_info_filtering_raises(
    client,
    session,
    backend_service_account_headers,
):
    crud.event.create(
        session,
        title=f"test event for filtering by info",
        description="test description",
        level="normal",
        info={"work_id": 1234, "boolean": True},
    )

    get_events_response = client.get(
        f"/v1/events",
        params={"info_jsonpath_match": "invalid json path"},
        headers=backend_service_account_headers,
    )

    assert get_events_response.status_code == 400


def test_event_crud_optional_filtering_by_string(
    session,
):
    # Create a few events
    crud.event.create(
        session,
        title=f"test event for filtering by info",
        description="test description",
        level="normal",
        info={"work_id": 1234, "string": "match"},
    )
    crud.event.create(
        session,
        title=f"test event for filtering by info",
        description="test description",
        level="normal",
        info={"work_id": 0, "string": "Not a Match"},
    )

    # Test that we can filter events using optional info keys
    events = crud.event.get_all_with_optional_filters(
        session,
        info_jsonpath_match='($.string == "match")',
    )

    assert len(events) >= 1

    for e in events:
        assert "string" in e.info
        assert e.info["string"] == "match"


def test_event_crud_optional_filtering_missing_attribute(
    session,
):
    # Create a few events
    crud.event.create(
        session,
        title=f"test event for filtering by info",
        description="test description",
        level="normal",
        info={"work_id": 1234, "boolean": True},
    )
    crud.event.create(
        session,
        title=f"test event for filtering by info",
        description="test description",
        level="normal",
        info={"work_id": 0, "boolean": False, "missing": "value"},
    )

    # Test that we can filter events using optional info keys
    events = crud.event.get_all_with_optional_filters(
        session,
        info_jsonpath_match='$.missing == "value"',
    )
    assert len(events) >= 1
    for e in events:
        assert "missing" in e.info
        assert e.info["missing"] == "value"


def test_event_crud_optional_filtering_bool_attribute(
    session,
):
    # Create a few events
    crud.event.create(
        session,
        title=f"test event for filtering by info",
        description="test description",
        level="normal",
        info={"work_id": 1234, "boolean": True},
    )
    crud.event.create(
        session,
        title=f"test event for filtering by info",
        description="test description",
        level="normal",
        info={"work_id": 0, "boolean": False, "missing": "value"},
    )

    # Test that we can filter events using boolean values
    events = crud.event.get_all_with_optional_filters(
        session,
        info_jsonpath_match="$.boolean == true",
    )
    assert len(events) >= 1
    for e in events:
        assert "boolean" in e.info
        assert e.info["boolean"] == True


def test_event_api_filter_since_timestamp(
    session,
    client,
    backend_service_account_headers,
):
    # create an event before the timestamp
    unwanted_title = f"unwanted_{random_lower_string(6)}"
    crud.event.create(
        session,
        title=unwanted_title,
        level="normal",
    )

    cutoff_time = datetime.datetime.utcnow()

    # create some events after the timestamp
    wanted_title = f"wanted_{random_lower_string(6)}"
    crud.event.create(
        session,
        title=wanted_title,
        level="normal",
    )

    # test that we can filter events using since
    get_events_response = client.get(
        f"/v1/events",
        params={"limit": 2, "since": cutoff_time.isoformat()},
        headers=backend_service_account_headers,
    )
    get_events_response.raise_for_status()
    events = get_events_response.json()["data"]

    all_titles = [e["title"] for e in events]

    assert unwanted_title not in all_titles
    assert wanted_title in all_titles

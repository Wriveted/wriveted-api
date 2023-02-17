from starlette import status

from app.models.edition import Edition
from app.schemas.edition import EditionUpdateIn


def test_update_edition_work(client, backend_service_account_headers, works_list):
    test_work = works_list[0]
    test_other_work = works_list[1]

    test_edition: Edition = test_work.editions[0]

    edition_update_with_new_work = EditionUpdateIn(
        work_id=test_other_work.id,
    )

    update_response = client.patch(
        f"v1/edition/{test_edition.isbn}",
        json=edition_update_with_new_work.dict(exclude_unset=True),
        headers=backend_service_account_headers,
    )
    update_response.raise_for_status()
    assert update_response.json()["work_id"] == str(test_other_work.id)

    edition_update_with_og_work = EditionUpdateIn(
        work_id=test_work.id,
    )

    revert_response = client.patch(
        f"v1/edition/{test_edition.isbn}",
        json=edition_update_with_og_work.dict(exclude_unset=True),
        headers=backend_service_account_headers,
    )
    revert_response.raise_for_status()
    assert revert_response.json()["work_id"] == str(test_work.id)

    response = client.get("v1/lists", headers=backend_service_account_headers)

    assert response.status_code == status.HTTP_200_OK


def test_update_edition_details(client, backend_service_account_headers, works_list):
    test_work = works_list[0]
    test_edition: Edition = test_work.editions[0]

    new_title = test_edition.edition_title + "_renamed"

    new_info = {"other": {"foo": "bar"}}

    edition_update_with_new_title_and_info = EditionUpdateIn(
        edition_title=new_title, info=new_info
    )

    update_response = client.patch(
        f"v1/edition/{test_edition.isbn}",
        json=edition_update_with_new_title_and_info.dict(exclude_unset=True),
        headers=backend_service_account_headers,
    )
    update_response.raise_for_status()

    # The response should include the new title
    assert update_response.json()["title"] == new_title
    assert update_response.json()["info"]["other"]["foo"] == "bar"

    info_to_merge = {"other": {"baz": "qux"}}
    edition_update_with_info_to_merge = EditionUpdateIn(info=info_to_merge)

    to_merge_payload = edition_update_with_info_to_merge.dict(exclude_unset=True)

    merge_response = client.patch(
        f"v1/edition/{test_edition.isbn}?merge_dicts=true",
        json=to_merge_payload,
        headers=backend_service_account_headers,
    )
    merge_response.raise_for_status()
    merged_info = merge_response.json()["info"]
    # check the original data is still there
    assert merged_info["other"]["foo"] == "bar"
    # check the new data is added
    assert merged_info["other"]["baz"] == "qux"

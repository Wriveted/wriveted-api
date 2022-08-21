import random

import httpx


def get_or_create_test_school(wriveted_api_host, admin_token, test_school_id=42):
    print(f"Host: {wriveted_api_host}, key: {admin_token}")

    test_school_response = httpx.get(
        f"{wriveted_api_host}/v1/school/784039ba-7eda-406d-9058-efe65f62f034",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=30,
    )
    if test_school_response.status_code > 500:
        raise ValueError
    # test_school_response = httpx.get(
    #     f"{wriveted_api_host}/v1/schools",
    #     params={"country_code": "ATA", "official_identifier": 42},
    #     headers={"Authorization": f"Bearer {admin_token}"},
    #     timeout=30,
    # )

    if test_school_response.status_code == 200 and len(test_school_response.json()) > 0:
        print("Test school already exists!")
        school_info = test_school_response.json()
    else:
        print("Creating test school")
        new_test_school_response = httpx.post(
            f"{wriveted_api_host}/v1/school",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": f"Test School - {test_school_id}",
                "country_code": "ATA",
                "official_identifier": test_school_id,
                "info": {
                    "msg": "Created for test purposes",
                    "location": {"state": "NSW", "postcode": 2000},
                },
            },
            timeout=30,
        )
        new_test_school_response.raise_for_status()
        school_info = new_test_school_response.json()
        # Mark it as active
        update_response = httpx.patch(
            f"{wriveted_api_host}/v1/school/{school_info['wriveted_identifier']}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "state": f"ACTIVE",
            },
            timeout=30,
        )

    return school_info


def get_or_create_random_class(
    wriveted_api_host, access_token, school_wriveted_identifier
):
    # List the classes, and if there are < 10 create a new one. Then return one at random
    school_classes = httpx.get(
        f"{wriveted_api_host}/v1/classes",
        params={"school_id": school_wriveted_identifier, "limit": 10},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    ).json()["data"]
    if len(school_classes) < 10:
        print("Creating a new class")
        new_class = httpx.post(
            f"{wriveted_api_host}/v1/school/{school_wriveted_identifier}/class",
            json={
                "name": f"Locust Class {1 + len(school_classes)} - {random.randint(1000, 10000000)}",
                # "school_id": school_wriveted_identifier,
            },
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        ).json()
        print("new class", new_class)
        return new_class
    else:
        class_brief = random.choice(school_classes)
        # Need to return the more detailed info to include joining code
        return httpx.get(
            f"{wriveted_api_host}/v1/class/{class_brief['id']}",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        ).json()


def create_school_service_account(wriveted_api_host, school_wriveted_identifier):
    svc_account_detail_response = httpx.post(
        f"{wriveted_api_host}/v1/service-account",
        headers={"Authorization": f"Bearer {settings.WRIVETED_API_TOKEN}"},
        json={
            "name": "Script created test account",
            "type": "school",
            "schools": [
                {
                    "wriveted_identifier": school_wriveted_identifier,
                }
            ],
        },
    )
    return svc_account_detail_response.json()


if __name__ == "__main__":
    from examples.config import settings

    admin_token = settings.WRIVETED_API_TOKEN
    api_host = settings.WRIVETED_API.rsplit("/")[0]

    school_info = get_or_create_test_school(api_host, admin_token)
    print(school_info)
    print("Creating LMS Account for test school")

    svc_account_details = create_school_service_account(
        api_host, school_info["wriveted_identifier"]
    )
    print(svc_account_details)

    # Note we can edit a service account with an HTTP PUT
    # E.g. linking to another school, or editing the name
    svc_account_detail_response = httpx.put(
        f"{settings.WRIVETED_API}/v1/service-account/{svc_account_details['id']}",
        headers={"Authorization": f"Bearer {settings.WRIVETED_API_TOKEN}"},
        json={
            "name": "Test school service account with updated name",
        },
    )

    print(svc_account_detail_response.status_code)
    print(svc_account_detail_response.json())

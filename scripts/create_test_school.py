import httpx
from examples.config import settings

admin_token = settings.WRIVETED_API_TOKEN
test_school_id = 42

test_school_response = httpx.get(
    f"{settings.WRIVETED_API}/v1/school/ATA/{test_school_id}",
    headers={"Authorization": f"Bearer {admin_token}"},
)
print(test_school_response.status_code)
print(test_school_response.text)
if test_school_response.status_code == 200:
    print("School already exists!")
    school_info = test_school_response.json()
else:
    print("Creating test school")
    new_test_school_response = httpx.post(
        settings.WRIVETED_API + "/v1/school",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": f"Test School - {test_school_id}",
            "country_code": "ATA",
            "official_identifier": test_school_id,
            "info": {
                "msg": "Created for test purposes",
                "location": {
                    "state": "NSW",
                    "postcode": 2000
                }
            },
        },
    )
    print(new_test_school_response.text)
    new_test_school_response.raise_for_status()
    school_info = new_test_school_response.json()

print(school_info)
print("Creating LMS Account for test school")

svc_account_detail_response = httpx.post(
    f"{settings.WRIVETED_API}/v1/service-account",
    headers={"Authorization": f"Bearer {settings.WRIVETED_API_TOKEN}"},
    json={
        "name": "Script created test account",
        "type": "school",
        "schools": [
            {
                "wriveted_identifier": school_info["wriveted_identifier"],
            }
        ],
        "info": {"initial info": test_school_id},
    },
)

print(svc_account_detail_response.status_code)
svc_account_details = svc_account_detail_response.json()
print(svc_account_details)
svc_account_detail_response.raise_for_status()

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

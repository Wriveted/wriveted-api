import time
import json
from pprint import pprint

import httpx

from config import settings


def get_all_aus_schools():
    schools_response = httpx.get(
        f"{settings.WRIVETED_API}/v1/schools",
        headers={"Authorization": f"Bearer {settings.WRIVETED_API_TOKEN}"},
        params={
            #'is_active': True,
            "limit": 100_000,
            "country_code": "AUS",
        },
        timeout=60,
    )
    return schools_response.json()


print("Getting all Australian schools from Wriveted")
aus_schools = get_all_aus_schools()
schools_by_acara = {s["official_identifier"]: s for s in aus_schools}
print("analyzing")


def get_school_by_acara_id(acara_id):
    school = schools_by_acara[acara_id]
    return school["wriveted_identifier"], school["info"]


def update_wriveted_school_info(wriveted_id, info):
    response = httpx.put(
        f"{settings.WRIVETED_API}/v1/school/{wriveted_id}",
        headers={"Authorization": f"Bearer {settings.WRIVETED_API_TOKEN}"},
        json={"info": info},
        timeout=10,
    )
    if response.status_code != 200:
        print("Failed!")
        print("Info was", info)
        print(response.text)
        print(response.headers)

    response.raise_for_status()
    return response.json()


print("Script to add all australian schools to Wriveted via the API")

print("Checking the connection")
print(httpx.get(settings.WRIVETED_API + "/v1/version").json())

with open("aus-schools.json") as raw_file:
    raw_data = json.load(raw_file)
print(f"Have {len(raw_data)} schools")
pprint(raw_data[0])

for school_data in raw_data:
    # 'ACARAId', 'SchoolURL', 'SchoolName'
    school_name = school_data["SchoolName"]
    acara_ID = school_data["ACARAId"]
    school_url = school_data["SchoolURL"]

    try:
        wriveted_id, info = get_school_by_acara_id(acara_ID)
    except KeyError:
        # Probably not an active school as we don't have them in the Wriveted DB
        continue

    if info.get("URL") is None and len(school_url) > 0:
        print(f"<{school_name}> - {wriveted_id}")
        print(f"  {acara_ID} - {school_url}")
        info["URL"] = school_url
        update_wriveted_school_info(wriveted_id, info)
        time.sleep(0.5)
    else:
        print(f"Skipping {school_name}")

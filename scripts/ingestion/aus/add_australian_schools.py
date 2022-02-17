import time
import json
import httpx

from config import settings

print("Script to add all australian schools to Wriveted via the API")

print("Checking the connection")
print(httpx.get(settings.WRIVETED_API + "/v1/version").json())


with open("aus-schools.json") as raw_file:
    raw_data = json.load(raw_file)

# Prepare for upload via the Wriveted API
school_data = []

for i, school in enumerate(raw_data):
    if len(school["AddressList"]) == 0:
        print("No address data for")
        print(i, school)

    if len(school["AddressList"]) > 1:
        print("Longer!")
        print(i, school)

    address = school["AddressList"][0]
    school_data.append(
        {
            "name": school["SchoolName"],
            "country_code": "AUS",
            "official_identifier": school["ACARAId"],
            "state": "inactive",
            "info": {
                # Anything can go here, so we save all the data we have
                "URL": school["SchoolURL"],
                "location": {
                    "suburb": address["City"],
                    "state": address["StateProvince"],
                    "postcode": address["PostalCode"],
                    "lat": address["GridLocation"]["Latitude"],
                    "long": address["GridLocation"]["Longitude"],
                },
                "type": school["SchoolType"],
                "sector": school["SchoolSector"],
            },
            # If it were available we could add these domain names:
            # "student_domain": "unknown",
            # "teacher_domain": "unknown"
        }
    )


print(f"Uploading {len(school_data)} schools in bulk to Wriveted API")

# An account Token with sufficient rights to add schools in bulk
api_token = settings.WRIVETED_API_TOKEN


response = httpx.get(
    settings.WRIVETED_API + "/v1/schools",
    headers={"Authorization": f"Bearer {api_token}"},
)
response.raise_for_status()
print("Current schools:")
print(response.json())

start_time = time.time()
response = httpx.post(
    settings.WRIVETED_API + "/v1/schools",
    json=school_data,
    headers={"Authorization": f"Bearer {api_token}"},
)
response.raise_for_status()
print(response.json())
end_time = time.time()

print("Finished")
print(end_time - start_time)

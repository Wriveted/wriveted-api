import csv
import time

import httpx
from config import settings

print("Script to add all New Zealand Schools to Wriveted via the API")

print("Checking the connection")
print(httpx.get(settings.WRIVETED_API + "/v1/version").json())


csv_data = httpx.get(settings.NZ_SCHOOL_DATA_URL).text

with open("nz-schools.csv", "wt") as raw_file:
    raw_file.write(csv_data)

print("Downloaded NZ Schools CSV")

# Prepare for upload via the Wriveted API
school_data = []

with open("nz-schools.csv") as csv_file:
    reader = csv.DictReader(csv_file, delimiter=",")
    header = next(reader)

    for i, school in enumerate(reader):
        print(school)

        school_data.append(
            {
                "name": school["Org_Name"],
                "country_code": "NZL",
                "official_identifier": school["School_Id"],
                "state": "inactive",
                "info": {
                    # Anything can go here, so we save all the data we have
                    "URL": school["URL"],
                    "location": {
                        "address": school["Add1_Line1"],
                        "state": school["Education_Region"],
                        "suburb": school["Add1_Suburb"],
                        "city": school["Add1_City"],
                        "postcode": (
                            school["Add1_Postal_Code"]
                            if "Add1_Postal_Code" in school
                            else (
                                school["Add2_Postal_Code"]
                                if "Add2_Postal_Code"
                                else None
                            )
                        ),
                        "lat": school["Latitude"],
                        "long": school["Longitude"],
                    },
                    "type": school["Org_Type"],
                    # "sector": school["SchoolSector"],
                },
                # If it were available we could add these domain names:
                # "student_domain": "unknown",
                # "teacher_domain": "unknown"
            }
        )


def batch(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx : min(ndx + n, l)]


# An account Token with sufficient rights to add schools in bulk
api_token = settings.WRIVETED_API_TOKEN

start_time = time.time()
for school_data_batch in batch(school_data, 500):
    print(f"Uploading {len(school_data_batch)} schools in bulk to Wriveted API")

    response = httpx.post(
        settings.WRIVETED_API + "/v1/schools",
        json=school_data,
        headers={"Authorization": f"Bearer {api_token}"},
        timeout=60,
    )
    response.raise_for_status()
    print(response.json())

end_time = time.time()

print("Finished")
print(end_time - start_time)

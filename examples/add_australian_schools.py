import csv
import time

import httpx

from examples.config import settings

print("Script to add all australian schools to Wriveted API")
print("Connecting")
print(httpx.get(settings.WRIVETED_API + "/version").json())

school_data = []

with open("australian_schools.csv", newline='') as csv_file:
    reader = csv.reader(csv_file)

    # Eat the header line
    headers = next(reader)

    for i, school_row in enumerate(reader):
        print(i, school_row[0], school_row[1])

        if school_row[7] == "Open":
            school_data.append(
                {
                    "name": school_row[1],
                    "country_code": "AUS",
                    "official_identifier": school_row[0],
                    "info": {
                        # Anything can go here, so we save all the data we have
                        "location": {
                            "suburb": school_row[2],
                            "state": school_row[3],
                            "postcode": school_row[4],
                            "geolocation": school_row[8],
                            "lat": school_row[11],
                            "long": school_row[12],
                        },
                        "type": school_row[5],
                        "sector": school_row[6],
                        "status": school_row[7],
                        "age_id": school_row[10]
                    },
                    # If it were available we could add these domain names:
                    #"student_domain": "unknown",
                    #"teacher_domain": "unknown"
                }
            )

print("Uploading in bulk")

# A User Account Token
user_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2NDE1MzAyNDMsImlhdCI6MTY0MDgzOTA0Mywic3ViIjoid3JpdmV0ZWQ6dXNlci1hY2NvdW50OjQyNmZhZGRmLWY0MTYtNGQ0ZS1hYjQwLWY2MWQ3ODBhOGNiZiJ9.hqn8tiv_QwymELIk-dsOr9KFb_LQ0yil2omrO-pncSw"


response = httpx.get(
    settings.WRIVETED_API + "/schools",
    headers={
        "Authorization": f"Bearer {user_token}"
    }
)
response.raise_for_status()
print("Current schools")
print(response.json())

start_time = time.time()
response = httpx.post(
    settings.WRIVETED_API + "/schools",
    json=school_data,
    headers={
        "Authorization": f"Bearer {user_token}"
    }
)
response.raise_for_status()
print(response.json())
end_time = time.time()

print("Finished")
print(end_time - start_time)

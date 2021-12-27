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
start_time = time.time()
httpx.post(settings.WRIVETED_API + "/schools", json=school_data)
end_time = time.time()

print("Finished")
print(end_time - start_time)

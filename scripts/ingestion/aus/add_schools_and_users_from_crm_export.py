import time
import json
from typing import Optional

import httpx
import csv

import pydantic
from pydantic import validator

from config import settings

print("Script to add known contacts to Wriveted via the API")

print(f"Connected to {settings.WRIVETED_API}")
print(httpx.get(settings.WRIVETED_API + "/v1/version").json())

"""
The csv should contain these columns:
    'Contact ID',
    'First Name',
    'Last Name',
    'School Size',
    'State/Region',
    '🏫 School name',
    'Country/Region',
    'Job Title',
    'Email Domain',
    '💻 School Library Management System',
    'Email',
    'Associated Company'
"""
csv_file = csv.reader(open("hubspot-crm-exports-all-contacts-2022-01-13.csv", newline=''))
header = next(csv_file)


class Contact(pydantic.BaseModel):
    id: int
    first_name: str
    last_name: str
    title: Optional[str]

    school_size: Optional[int]
    school_name: str
    country: str

    school_email_domain: str

contacts = []
# First try find all the schools.
for line in csv_file:
    print(line)

    Contact(

    )

    raise SystemExit


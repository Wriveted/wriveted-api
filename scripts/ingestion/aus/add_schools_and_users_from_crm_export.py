# Ensure your environment variables are set such that this script can connect
# directly to the database. E.g. if running via docker-compose
import os

from app.schemas.user import UserCreateIn

os.environ['POSTGRESQL_SERVER'] = 'localhost/'
#os.environ['POSTGRESQL_PASSWORD'] = ''
os.environ['SECRET_KEY'] = 'CHrUJmNw1haKVSorf3ooW-D6eRooePyo-V8II--We78'

# Note we have to set at least the above environment variables before importing our application code

from app import crud, api, db, models, schemas
from app import config
from app.db.session import get_session
from app.api.dependencies.security import create_user_access_token

import time
import json
from typing import Optional

import httpx
import csv

import pydantic
from pydantic import EmailStr

settings = config.get_settings()
session = next(get_session(settings=settings))

print("Script to add known contacts to Wriveted via the API")


csv_file = csv.reader(open("hubspot-crm-exports-all-contacts-2022-01-13.csv", newline=''))
header = next(csv_file)


class Contact(pydantic.BaseModel):
    id: int
    first_name: str
    last_name: str
    title: Optional[str]
    school_size: Optional[int]
    school_official_id: Optional[str]
    state_or_region: str
    school_name: str
    country: str
    job_title: Optional[str]
    school_email_domain: str
    school_specific_email_domain: Optional[str]
    library_management_system: Optional[str]
    email: EmailStr
    associated_company: str


contacts = []
# First try find all the schools.
for line in csv_file:
    contact = Contact(
        id=line[0],
        school_official_id=line[1],
        first_name=line[2],
        last_name=line[3],
        school_size=line[4] if len(line[4]) else None,
        state_or_region=line[5],
        school_name=line[6],
        country=line[7],
        job_title=line[8],
        school_email_domain=line[9],
        school_specific_email_domain=line[10],
        library_management_system=line[11],
        email=line[12],
        associated_company=line[13],

    )

    contacts.append(contact)

print(f"Loaded {len(contacts)} contacts from CRM export")

# Add User accounts for all the contacts, include the CRM contact ID and job title.
users = []
for contact in contacts:
    user = crud.user.create(
        db=session,
        obj_in=UserCreateIn(
            name=f"{contact.first_name.title()} {contact.last_name.title()}",
            email=contact.email,
            info={"other": {
                "job_title": contact.job_title,
                "associated_company": contact.associated_company
            }},
        ),
        commit=False
    )
    users.append(user)

    # First if the official ID is provided use that.
    country_code = "AUS" if contact.country == "Australia" else "USA"

    if contact.school_official_id is not None:
        school = crud.school.get_by_official_id_or_404(
            db=session,
            country_code=country_code,
            official_id=contact.school_official_id
        )
    else:

        schools = crud.school.get_all_with_optional_filters(
            db=session,
            country_code=country_code,
            query_string=contact.school_name
        )
        if len(schools) == 1:
            print(contact.id, schools[0].official_identifier)

            school = schools[0]
        elif len(schools) == 0:
            print("Skipping missing school:")
            print(contact)
            print(schools)
            # Let's make the school
            continue
        elif len(schools) > 1:
            print("there were multiple schools found")
            print(contact)
            print(schools)


    # Add the user to the school. Update the school with domains etc
    school.users.append(user)



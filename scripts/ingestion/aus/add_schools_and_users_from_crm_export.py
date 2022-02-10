# Ensure your environment variables are set such that this script can connect
# directly to the database. E.g. if running via docker-compose
import os

from app.models import SchoolState
from app.models.user import UserAccountType
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
    associated_company: Optional[str]


contacts = []
# First try find all the schools.
for line in csv_file:

    contact = Contact(
        id=line[0].strip(),
        school_official_id=line[1] if len(line[1]) > 1 else None,
        first_name=line[2].strip(),
        last_name=line[3].strip(),
        school_size=line[4] if len(line[4]) > 1 else None,
        state_or_region=line[5].strip(),
        school_name=line[6].strip(),
        country=line[7].strip(),
        job_title=line[8].strip() if len(line[8]) > 1 else None,
        school_email_domain=line[9].strip(),
        school_specific_email_domain=line[10].strip(),
        library_management_system=line[11].strip(),
        email=line[12].strip(),
        associated_company=line[13].strip() if len(line[13]) > 1 else None,

    )

    contacts.append(contact)

print(f"Loaded {len(contacts)} contacts from CRM export")

# Add User accounts for all the contacts, include the CRM contact ID and job title.
users = []

unhandled_contacts = []

for contact in contacts:
    user, created = crud.user.get_or_create(
        db=session,
        user_data=UserCreateIn(
            name=f"{contact.first_name.title()} {contact.last_name.title()}",
            email=contact.email,
            info={
                "other": {
                    "job_title": contact.job_title,
                    "associated_company": contact.associated_company
                }
            },
        ),
        commit=False
    )
    users.append(user)

    # First if the official ID is provided use that.
    country_code = "AUS" if contact.country == "Australia" else "USA"

    if contact.school_official_id is not None:
        try:
            school = crud.school.get_by_official_id_or_404(
                db=session,
                country_code=country_code,
                official_id=contact.school_official_id
            )
        except:
            print(f"Was told that {contact.school_official_id} was an official ID but couldn't find it?")
            raise
    else:
        schools = crud.school.get_all_with_optional_filters(
            db=session,
            country_code=country_code,
            query_string=contact.school_name
        )
        if len(schools) == 1:
            # We lucked out and found just one school with that name in this country.
            print(contact.id, schools[0].official_identifier)
            school = schools[0]
        elif len(schools) == 0:
            if contact.country == "Australia":
                raise SystemExit("Australian School Missing")
            else:
                # Let's make the USA schools later
                unhandled_contacts.append(contact)
                pass
            continue
        elif len(schools) > 1:
            raise SystemExit("there were multiple schools found")

    # If we made it here we have one school.
    # Associate the user and the found school.
    user.school = school
    user.type = UserAccountType.LIBRARY

    # Now mark the school as active
    school.state = SchoolState.ACTIVE

    # Update the school with any info from the contact string

    session.commit()

print()
print("Non-Aus schools:")
for i, contact in enumerate(unhandled_contacts, start=1):
    print(i, contact.school_name, f"{contact.state_or_region}, {contact.country}")

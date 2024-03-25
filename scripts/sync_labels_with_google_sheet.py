"""
This script syncs a Google Sheet with Wriveted.

The sheet is expected to have a particular structure:
- "Books" sheet and "Config" sheet
- Input columns Published Year, ISBN, Title, Age, Hue, Publisher - data starting at "Books"!B2

- Optional Wriveted Booklist ID in "Config"!B2 (otherwise creates a new booklist)

The script will load the ISBNs from the Books sheet, and add output columns for
the Wriveted Data.

You will need Google Authorization credentials for a desktop application.
To learn how to create credentials for a desktop application, refer to
https://developers.google.com/workspace/guides/create-credentials

(ensure there is a `credentials.json` in the current working directory)

"""

import os.path

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pydantic import BaseModel, validator

from examples.config import settings

api_token = settings.WRIVETED_API_TOKEN

wriveted_api_response = httpx.get(
    f"{settings.WRIVETED_API}/v1/version",
    headers={"Authorization": f"Bearer {api_token}"},
    timeout=20,
)
wriveted_api_response.raise_for_status()
print(f"Connected to wriveted api: {settings.WRIVETED_API}")

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]


# The ID and range of the spreadsheet.
SPREADSHEET_ID = "1MBD7AN2CeN8KxC_KsIoe6vH8-OlY1pjmn_Zi5H1P2P8"

# Ranges
# Use R1C1 notation to avoid column ZZ etc
starting_row = 2
ending_row = 350
INPUT_RANGE_NAME = f"Books!B{starting_row}:G{ending_row}"
OUTPUT_HEADINGS_RANGE = "Books!J1:Z1"
OUTPUT_RANGE_NAME = f"Books!J{starting_row}:Z{ending_row}"


# Test write to sheet:
# range_start = f"R2C9"
# range_end = f"R5C14"
# vert_range = f"{range_start}:{range_end}"
# update_sheet_data(sheets_service, vert_range, [['col1 row 1', 'col2 row 1'], ['col 1 row 2', 'col 2 row 2']])


class InputDataRow(BaseModel):
    year: int | None
    isbn: str
    title: str
    age: int | None
    primary_hue: str | None
    publisher: str | None

    @validator("year", pre=True)
    def skip_blank_year(cls, v):
        if v == "":
            return None
        else:
            return v

    @validator("age", pre=True)
    def skip_blank_age(cls, v):
        if v == "":
            return None
        else:
            return v


def main():
    """ """
    creds = google_auth()
    sheets_service = build("sheets", "v4", credentials=creds).spreadsheets()

    isbn_to_wriveted_edition_info = {}
    work_ids = set()

    # Add the headings for edition data
    headings = [
        "Recommend Status",
        "Hues",
        "Age (min)",
        "Age (Max)",
        "Reading Ability",
        "Huey Summary",
        "Pages",
        "Title",
        "Authors",
        "Illustrators",
        "Date Published",
        "Admin Link",
    ]
    update_sheet_data(sheets_service, OUTPUT_HEADINGS_RANGE, [headings])

    # Read the input data from the sheet
    range = INPUT_RANGE_NAME
    values = read_sheet_data(sheets_service, range)

    for row_number, row in enumerate(values, start=starting_row):
        parsed_row = InputDataRow(
            year=row[0],
            isbn=row[1],
            title=row[2],
            age=row[3],
            primary_hue=row[4] if len(row) > 4 else None,
            publisher=row[5] if len(row) > 5 else None,
        )

        wriveted_api_response = httpx.get(
            f"{settings.WRIVETED_API}/v1/edition/{parsed_row.isbn}",
            headers={"Authorization": f"Bearer {api_token}"},
            timeout=50,
        )
        if wriveted_api_response.status_code != 200:
            print(wriveted_api_response.status_code)
            print(wriveted_api_response.text)
        edition_info = wriveted_api_response.json()
        if (
            edition_info.get("work_id") is not None
            and edition_info.get("work_id") not in work_ids
        ):
            print(
                f"Row {row_number} has Wriveted work_id {edition_info['work_id']} - {edition_info['title']}"
            )
            # Might as well keep note of which row it was
            edition_info["row_number"] = row_number
            isbn_to_wriveted_edition_info[parsed_row.isbn] = edition_info
            work_ids.add(edition_info["work_id"])

            # Now get the work detail too
            wriveted_api_response = httpx.get(
                f"{settings.WRIVETED_API}/v1/work/{edition_info['work_id']}",
                headers={"Authorization": f"Bearer {api_token}"},
                timeout=30,
            )
            wriveted_api_response.raise_for_status()
            work_detail_response = wriveted_api_response.json()
            isbn_to_wriveted_edition_info[parsed_row.isbn][
                "work-detail"
            ] = work_detail_response
        else:
            print(
                f"Skipping row {row_number} (no corresponding work found in Wriveted DB or is duplicate work)"
            )
            continue
        # Prepare the update
        isbn = parsed_row.isbn
        data = isbn_to_wriveted_edition_info[isbn]
        title = data["title"]
        authors = ", ".join(
            map(lambda a: f"{a['first_name']} {a['last_name']}", data["authors"])
        )
        illustrators = ", ".join(
            map(lambda a: f"{a['first_name']} {a['last_name']}", data["illustrators"])
        )
        published = (
            str(data["date_published"])[:4]
            if data["date_published"] is not None
            else ""
        )
        info = data["info"] if data["info"] is not None else {}
        pages = info.get("pages", "")
        work_id = data["work_id"]

        labelset = data.get("work-detail", {}).get("labelset")
        status = labelset["recommend_status"]
        hues = ", ".join(map(lambda h: h["name"], labelset.get("hues")))
        min_age = labelset.get("min_age")
        max_age = labelset.get("max_age")

        reading_abilities = ", ".join(
            map(lambda v: v["key"], labelset.get("reading_abilities"))
        )

        huey_summary = labelset.get("huey_summary")

        # Update the row
        # print("Update data", [status, hues, min_age, max_age, reading_abilities, pages, huey_summary, title, authors, illustrators, published, pages, f"https://api.wriveted.com/work/{work_id}/"])
        range_start = f"R{data['row_number']}C10"
        range_end = f"R{data['row_number']}C23"
        update_sheet_data(
            sheets_service,
            f"{range_start}:{range_end}",
            [
                [
                    status,
                    hues,
                    min_age,
                    max_age,
                    reading_abilities,
                    huey_summary,
                    pages,
                    title,
                    authors,
                    illustrators,
                    published,
                    f"https://api.wriveted.com/work/{work_id}/",
                ]
            ],
        )


def read_sheet_data(sheet, range):
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=range).execute()
    values = result.get("values", [])
    if not values:
        print(f"No data found at {range}")
        raise
    return values


def update_sheet_data(sheet, range, values):
    sheet.values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=range,
        valueInputOption="RAW",
        body={"values": values},
    ).execute()


def google_auth():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds


if __name__ == "__main__":
    main()

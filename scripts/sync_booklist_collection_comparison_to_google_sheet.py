"""
This script syncs a "Huey Book List" Google Sheet with Wriveted.

The sheet is expected to have a particular structure:
- "Books" sheet
- Column of ISBNs starting at C4
- Optional Wriveted Booklist ID in B2 (otherwise creates a new booklist)

The script will use the existing booklist or create a new one using the ISBNs
from the google sheet, will locate the schools that have uploaded their collections
and compare the booklist with the school's collection and update the sheet with
"In Collection" or "Not in collection".

You will need Google Authorization credentials for a desktop application.
To learn how to create credentials for a desktop application, refer to
https://developers.google.com/workspace/guides/create-credentials

(ensure there is a `credentials.json` in the current working directory)

The Google sheet (not in xlxs format) will need to be shared with the
IAM account <spreadsheet-user@wriveted-api.iam.gserviceaccount.com>


"""

import os.path

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.services.editions import get_definitive_isbn
from examples.config import settings

api_token = settings.WRIVETED_API_TOKEN

wriveted_api_response = httpx.get(
    f"{settings.WRIVETED_API}/v1/version",
    headers={"Authorization": f"Bearer {api_token}"},
    timeout=20,
)
wriveted_api_response.raise_for_status()
print(f"Connected to wriveted api: {settings.WRIVETED_API}")
wriveted_api_response = httpx.get(
    f"{settings.WRIVETED_API}/v1/auth/me",
    headers={"Authorization": f"Bearer {api_token}"},
    timeout=20,
)
wriveted_api_response.raise_for_status()
# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

# The ID and range of the spreadsheet to sync with
SPREADSHEET_ID = "1NsgNos_hubNEhhfvyJphl_M7xsfl8YzkqX0gjmachXs"

# SPREADSHEET_ID = "1-ePJhgwX9CkFUMOdVgHdrZxp9YmfnqU9sl_gVLslUbw"
ISBN_RANGE_NAME = "Books!A4:C104"


def main():
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
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

    try:
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()

        # Get the isbns from the sheet
        isbn_to_wriveted_edition_info = {}
        work_ids = set()
        result = (
            sheet.values()
            .get(spreadsheetId=SPREADSHEET_ID, range=ISBN_RANGE_NAME)
            .execute()
        )

        values = result.get("values", [])

        if not values:
            print("No ISBN data found at C4:")
            return

        for row in values:
            # Row is a list of strings where the cells are filled in - could be len 2 if ISBN missing
            if len(row) > 2:
                id, title, isbn = row
                isbn = get_definitive_isbn(isbn)
                wriveted_api_response = httpx.get(
                    f"{settings.WRIVETED_API}/v1/edition/{isbn}",
                    headers={"Authorization": f"Bearer {api_token}"},
                    timeout=10,
                )
                try:
                    wriveted_api_response.raise_for_status()
                except httpx.HTTPStatusError:
                    print(f"Skipping {isbn} (couldn't locate in Wriveted DB)")
                    continue

                edition_info = wriveted_api_response.json()
                if (
                    edition_info["work_id"] is not None
                    and edition_info["work_id"] not in work_ids
                ):
                    print(
                        f"Row id {id} has wriveted work id {edition_info['work_id']} - {edition_info['title']}"
                    )
                    edition_info["order_id"] = id
                    isbn_to_wriveted_edition_info[isbn] = edition_info
                    work_ids.add(edition_info["work_id"])
                else:
                    print(
                        f"Skipping row id {id} (no corresponding work found in Wriveted DB or work already in list)"
                    )
                    print(row)
                    print(edition_info)

    except HttpError as err:
        print(err)

    booklist_data = (
        sheet.values()
        .get(spreadsheetId=SPREADSHEET_ID, range="Books!B1:B2")
        .execute()
        .get("values", [])
    )
    booklist_name = booklist_data[0][0]
    booklist_id = booklist_data[1][0] if len(booklist_data) > 1 else None
    print(f"Booklist name '{booklist_name}'")
    print("Booklist id:", booklist_id)
    if booklist_id is None:
        # Create a new booklist on wriveted
        wriveted_api_response = httpx.post(
            f"{settings.WRIVETED_API}/v1/lists",
            headers={"Authorization": f"Bearer {api_token}"},
            timeout=20,
            json={
                "name": booklist_name,
                "type": "Huey",
                # "info": {}
                "items": [
                    {
                        "order_id": isbn_to_wriveted_edition_info[isbn]["order_id"],
                        "work_id": isbn_to_wriveted_edition_info[isbn]["work_id"],
                        "info": {"edition": isbn},
                    }
                    for isbn in isbn_to_wriveted_edition_info
                ],
            },
        )

        wriveted_api_response.raise_for_status()
        print("New booklist created")
        new_booklist_data = wriveted_api_response.json()
        booklist_id = new_booklist_data["id"]

        print("Adding booklist id to sheet (in B2)", booklist_id)
        sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range="Books!B2",
            valueInputOption="RAW",
            body={"values": [[booklist_id]]},
        ).execute()
    else:
        print("Using existing booklist")
        # Note this doesn't handle changes to the booklist

    # Now the comparison with particular school collections
    # Get the school ids for schools that have added their collections to Wriveted.
    wriveted_api_response = httpx.get(
        f"{settings.WRIVETED_API}/v1/schools",
        headers={"Authorization": f"Bearer {api_token}"},
        params={
            "country_code": "AUS",
            "is_active": True,
            "connected_collection": True,
            "limit": 50,
        },
        timeout=30,
    )
    wriveted_api_response.raise_for_status()
    wriveted_schools = wriveted_api_response.json()

    # Then, for each school compare with the booklist, then update the sheet

    wriveted_school_ids, wriveted_school_names, school_collection_size = zip(
        *[
            (s["wriveted_identifier"], s["name"], s["collection_count"])
            for s in wriveted_schools
        ]
    )

    # Use R1C1 notation to avoid column ZZ etc
    range_start = "R1C4"
    range_end = f"R3C{4 + len(wriveted_school_ids)}"
    (
        sheet.values()
        .update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"Books!{range_start}:{range_end}",
            valueInputOption="RAW",
            body={
                "values": [
                    wriveted_school_names,
                    wriveted_school_ids,
                    school_collection_size,
                ]
            },
        )
        .execute()
    )

    print("Updated school names")
    print(wriveted_school_ids)

    for column_index, (school_id, school_name) in enumerate(
        zip(wriveted_school_ids, wriveted_school_names), start=4
    ):
        print("Comparing booklist for school", school_name)
        wriveted_api_response = httpx.get(
            f"{settings.WRIVETED_API}/v1/school/{school_id}/collection/compare-with-booklist/{booklist_id}",
            headers={"Authorization": f"Bearer {api_token}"},
            timeout=30,
        )
        wriveted_api_response.raise_for_status()
        comparison_response = wriveted_api_response.json()

        # transform the response into a map of work_id -> {booklist item in collection}
        work_in_collection = {}

        for item in comparison_response["data"]:
            work_in_collection[item["work_id"]] = item

        # Update the sheet an entire column at a time
        values = ["" for _ in range(256)]

        for isbn in isbn_to_wriveted_edition_info:
            edition_info = isbn_to_wriveted_edition_info[isbn]
            # Note some rows might be missing!
            row_id = int(edition_info["order_id"])
            work_id = edition_info["work_id"]
            if work_id in work_in_collection:
                booklist_item_in_collection = work_in_collection[work_id][
                    "in_collection"
                ]
                values[row_id - 1] = (
                    "In collection"
                    if booklist_item_in_collection
                    else "Not in collection"
                )

        column_range = f"R4C{column_index}:R{4+len(values)}"

        sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"Books!{column_range}",
            valueInputOption="RAW",
            body={"values": [[v] for v in values]},
        ).execute()


if __name__ == "__main__":
    main()

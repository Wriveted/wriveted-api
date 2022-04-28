"""
This script syncs a "Huey Book List" Google Sheet with Wriveted.

You will need Google Authorization credentials for a desktop application.
To learn how to create credentials for a desktop application, refer to
https://developers.google.com/workspace/guides/create-credentials

TL;DR ensure there is a `credentials.json` in the current working directory.
Execute the script with

The sheet is expected to have a "Books" sheet with ISBNs in column C4.

This script gets the list of ISBNs and creates a booklist in Wriveted
Booklist name should be in B1

Then the script compares the booklist with any schools in the sheet.
School's Wriveted IDs should be in E2, F2 etc

Each school column will be output by the script if the item is in
the schools collection.
"""
import os.path

import httpx

from examples.config import settings

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

api_token = settings.WRIVETED_API_TOKEN

wriveted_api_response = httpx.get(
    f"{settings.WRIVETED_API}/v1/version",
    headers={"Authorization": f"Bearer {api_token}"},
)
wriveted_api_response.raise_for_status()
print(f"Connected to wriveted api: {settings.WRIVETED_API}")

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

# The ID and range of a sample spreadsheet.
SPREADSHEET_ID = "1-ePJhgwX9CkFUMOdVgHdrZxp9YmfnqU9sl_gVLslUbw"
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
                wriveted_api_response = httpx.get(
                    f"{settings.WRIVETED_API}/v1/edition/{isbn}",
                    headers={"Authorization": f"Bearer {api_token}"},
                )
                wriveted_api_response.raise_for_status()
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
    # Get the school ids, then compare with the booklist, then update the sheet
    wriveted_school_ids = (
        sheet.values()
        .get(spreadsheetId=SPREADSHEET_ID, range="Books!D2:Z2")
        .execute()
        .get("values", [])
    )[0]
    print(wriveted_school_ids)

    for school_id in wriveted_school_ids:
        print("Comparing booklist for school", school_id)
        wriveted_api_response = httpx.get(
            f"{settings.WRIVETED_API}/v1/school/{school_id}/collection/compare-with-booklist/{booklist_id}",
            headers={"Authorization": f"Bearer {api_token}"},
        )
        wriveted_api_response.raise_for_status()
        comparison_response = wriveted_api_response.json()

        # transform the response into a map of work_id -> {booklist item in collection}
        work_in_collection = {}

        for item in comparison_response["data"]:
            work_in_collection[item["work_id"]] = item

        # Update the sheet cell by cell because it looks cooler
        for isbn in isbn_to_wriveted_edition_info:
            edition_info = isbn_to_wriveted_edition_info[isbn]
            row_id = edition_info["order_id"]
            work_id = edition_info["work_id"]
            booklist_item_in_collection = work_in_collection[work_id]["in_collection"]
            # Sheet index is position + 3
            index = int(row_id) + 3

            sheet.values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f"Books!D{index}",
                valueInputOption="RAW",
                body={
                    "values": [
                        [
                            "In collection"
                            if booklist_item_in_collection
                            else "Not in collection"
                        ]
                    ]
                },
            ).execute()


if __name__ == "__main__":
    main()

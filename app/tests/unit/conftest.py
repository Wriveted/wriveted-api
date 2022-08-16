import pytest
from mock import MagicMock


@pytest.fixture(scope="module")
def sendgrid_email_search_response():
    response = MagicMock()
    response.to_dict = {
        "result": {
            "testaccount@sendgrid.com": {
                "contact": {
                    "address_line_1": "",
                    "address_line_2": "",
                    "alternate_emails": [],
                    "city": "",
                    "country": "",
                    "email": "testaccount@sendgrid.com",
                    "first_name": "",
                    "id": "",
                    "last_name": "",
                    "list_ids": [],
                    "segment_ids": [],
                    "postal_code": "",
                    "state_province_region": "",
                    "phone_number": "",
                    "whatsapp": "",
                    "line": "",
                    "facebook": "",
                    "unique_name": "",
                    "custom_fields": {},
                    "created_at": "",
                    "updated_at": "",
                }
            }
        }
    }
    return response

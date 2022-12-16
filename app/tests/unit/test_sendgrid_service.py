from app.schemas.sendgrid import SendGridContactData
from app.services.commerce import sendgrid_contact_response_to_obj


def test_sendgrid_email_search_to_contact(sendgrid_email_search_response):
    output = sendgrid_contact_response_to_obj(sendgrid_email_search_response)
    assert isinstance(output, SendGridContactData)
    assert output.email == "testaccount@sendgrid.com"

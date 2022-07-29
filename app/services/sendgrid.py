from structlog import get_logger
from sendgrid.helpers.mail import Mail, From
from sendgrid import SendGridAPIClient
from app import crud
from app.config import get_settings
from app.models.service_account import ServiceAccount
from app.models.user import User
from app.schemas.sendgrid import ContactData, EmailData
from sqlalchemy.orm import Session

logger = get_logger()
config = get_settings()


def upsert_sendgrid_contact(
    data: ContactData, session: Session, account: User | ServiceAccount
):
    """
    Upserts a Sendgrid contact with the provided data
    """
    try:
        sg = SendGridAPIClient(config.SENDGRID_API_KEY)
        response = sg.client.marketing.contacts.put(
            request_body={"contacts": [data.dict()]}
        )
        output = {
            "code": str(response.status_code),
            "body": str(response.body),
            "headers": str(response.headers),
        }

        error = None
    except Exception as e:
        error = "Error: {0}".format(e)

    crud.event.create(
        session=session,
        title="SendGrid contact upsert requested",
        description="A SendGrid contact was queued to be either created or updated",
        info={
            "result": "success" if not error else "error",
            "detail": error or output,
            "data": data.dict(),
        },
        account=account,
        commit=True,
        level="warning" if error else "debug",
    )


def send_sendgrid_email(
    data: EmailData, session: Session, account: User | ServiceAccount
):
    """Send a dynamic email to a list of email addresses

    :returns API response code
    :raises Exception e: raises an exception
    """
    message = Mail(from_email=data.from_email, to_emails=data.to_emails)

    if data.template_data:
        message.dynamic_template_data = data.template_data
    if data.template_id:
        message.template_id = data.template_id
    if data.from_name:
        message.from_email = From(data.from_email, data.from_name)

    error = None
    try:
        sg = SendGridAPIClient(config.SENDGRID_API_KEY)
        response = sg.send(message)
        output = {
            "code": str(response.status_code),
            "body": str(response.body),
            "headers": str(response.headers),
        }

    except Exception as e:
        error = "Error: {0}".format(e)

    crud.event.create(
        session=session,
        title="SendGrid email sent",
        description="An email was sent to a user via SendGrid",
        info={
            "result": "success" if not error else "error",
            "detail": error or output,
            "data": data.dict(),
        },
        account=account,
        commit=True,
        level="warning" if error else "debug",
    )

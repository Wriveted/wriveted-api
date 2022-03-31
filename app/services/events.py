from typing import Union

from sqlalchemy.orm import Session
from structlog import get_logger

from app.models import Event, ServiceAccount, User, EventLevel


logger = get_logger()


def create_event(
    session: Session,
    title: str,
    description: str = "",
    properties: dict = None,
    level: EventLevel = EventLevel.NORMAL,
    school=None,
    account: Union[ServiceAccount, User] = None,
    commit: bool = True,
):
    user = account if isinstance(account, User) else None
    service_account = account if isinstance(account, ServiceAccount) else None
    if properties is None:
        properties = {}
    properties["description"] = description
    event = Event(
        title=title,
        info=properties,
        level=level,
        school=school,
        user=user,
        service_account=service_account,
    )
    session.add(event)
    if commit:
        session.commit()
        session.refresh(event)

    # If an event was worth recording in the database we probably also want to log it
    logger.info(
        f"{title}\n{description}",
        level=level,
        school=school,
        user=user,
        service_account=service_account,
    )
    return event

from typing import Union

from sqlalchemy.orm import Session

from app.models import Event, ServiceAccount, User, EventLevel


def create_event(
    session: Session,
    title: str,
    description: str,
    level: EventLevel = EventLevel.NORMAL,
    school=None,
    account: Union[ServiceAccount, User] = None,
    commit: bool = True,
):
    user = account if isinstance(account, User) else None
    service_account = account if isinstance(account, ServiceAccount) else None

    event = Event(
        title=title,
        description=description,
        level=level,
        school=school,
        user=user,
        service_account=service_account,
    )
    session.add(event)
    if commit:
        session.commit()
        session.refresh(event)
    return event

# Ensure your environment variables are set such that this script can connect
# directly to the database. E.g. there are different postgres passwords if running
# via docker-compose versus a Cloud SQL database.
import os
from datetime import timedelta

from app.models import ServiceAccount
from app.schemas.users.user_create import UserCreateIn
from app.services.security import create_access_token

# os.environ["POSTGRESQL_SERVER"] = "localhost/"
os.environ["POSTGRESQL_SERVER"] = "localhost"
# os.environ['POSTGRESQL_PASSWORD'] = ''
# os.environ["SECRET_KEY"] = "CHrUJmNw1haKVSorf3ooW-D6eRooePyo-V8II--We78"

# Note we have to set at least the above environment variables before importing our application code

from app import api, config, crud, db, models, schemas
from app.api.dependencies.security import create_user_access_token
from app.db.session import SessionManager, get_session, get_session_maker

with SessionManager(get_session_maker()) as session:
    user = crud.user.get_by_account_email(db=session, email="hardbyte@gmail.com")
    # if user is None:
    #     user = crud.user.create(
    #         db=session, obj_in=UserCreateIn(name="Brian thorne", email="hardbyte@gmail.com")
    #     )
    #     user.type = "wriveted"
    #
    print("Generating admin user auth token")
    # print("Using secret key", config.get_settings().SECRET_KEY)
    print(create_user_access_token(user))

    huey_service_token_id = "e8467650-bc8a-4ca7-9052-176b33026a21"
    huey_service_account = crud.service_account.get(session, id=huey_service_token_id)
    print(huey_service_account)

    if huey_service_account is None:
        print("Creating service account")
        huey_service_account = ServiceAccount(
            id=huey_service_token_id,
            name="Huey",
            type="backend",
            description="Huey's service account",
        )
        session.add(huey_service_account)
        # session.commit()
    else:
        print("Service account already exists")

    print("Generating service account auth token")
    access_token = create_access_token(
        subject=f"wriveted:service-account:{huey_service_token_id}",
        expires_delta=timedelta(days=10),
    )
    print(access_token)

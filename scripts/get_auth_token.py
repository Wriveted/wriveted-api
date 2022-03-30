# Ensure your environment variables are set such that this script can connect
# directly to the database. E.g. there are different postgres passwords if running
# via docker-compose versus a Cloud SQL database.
import os

from app.schemas.user import UserCreateIn

os.environ["POSTGRESQL_SERVER"] = "localhost/"
# os.environ['POSTGRESQL_PASSWORD'] = ''
os.environ["SECRET_KEY"] = "CHrUJmNw1haKVSorf3ooW-D6eRooePyo-V8II--We78"

# Note we have to set at least the above environment variables before importing our application code

from app import crud, api, db, models, schemas
from app import config
from app.db.session import get_session
from app.api.dependencies.security import create_user_access_token

session = next(get_session(settings=config.get_settings()))

user = crud.user.get_by_account_email(db=session, email="hardbyte@gmail.com")
if user is None:
    user = crud.user.create(db=session, obj_in=UserCreateIn(
        name="Brian", email="hardbyte@gmail.com"
    ))
    user.type = "wriveted"

print("Generating auth token")
print(create_user_access_token(user))

# Ensure your environment variables are set such that this script can connect
# directly to the database. E.g. there are different postgres passwords if running
# via docker-compose versus a Cloud SQL database.
import os

from app.schemas.users.user_create import UserCreateIn
from app.schemas.users.user_update import InternalUserUpdateIn

os.environ["POSTGRESQL_SERVER"] = "localhost/"
# os.environ['POSTGRESQL_PASSWORD'] = ''
os.environ["SECRET_KEY"] = "CHrUJmNw1haKVSorf3ooW-D6eRooePyo-V8II--We78"

# Note we have to set at least the above environment variables before importing our application code

from app import config, crud
from app.api.dependencies.security import create_user_access_token
from app.db.session import get_session

session = next(get_session())

email = "brian@wriveted.com"

user = crud.user.get_by_account_email(db=session, email=email)
if user is None:
    print("Creating new admin user")
    user = crud.user.create(
        db=session,
        obj_in=UserCreateIn(name="Developer", email=email, type="wriveted"),
    )
elif user.type != "wriveted":
    print("Updating user to wriveted admin")
    crud.user.update(
        db=session, obj_in=InternalUserUpdateIn(current_type=user.type, type="wriveted")
    )
else:
    print("Using existing admin user")

print("Generating auth token")
print(create_user_access_token(user))

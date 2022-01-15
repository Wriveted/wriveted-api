# Ensure your environment variables are set such that this script can connect
# directly to the database. E.g. if running via docker-compose
import os
os.environ['POSTGRESQL_SERVER'] = 'localhost/'
os.environ['POSTGRESQL_PASSWORD'] = 'xvc8kcn'
os.environ['SECRET_KEY'] = 'CHrUJmNw1haKVSorf3ooW-D6eRooePyo-V8II--We78'

from app import crud, api, db, models, schemas
from app import config
from app.db.session import get_session
from app.api.dependencies.security import create_user_access_token

session = next(get_session())

user = crud.user.get_all(db=session, limit=1)[0]
print("Generating auth token")
print(create_user_access_token(user))


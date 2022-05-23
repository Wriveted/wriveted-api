# Ensure your environment variables are set such that this script can connect
# directly to the database. E.g. there are different postgres passwords if running
# via docker-compose versus a Cloud SQL database.
import os

os.environ["POSTGRESQL_SERVER"] = "localhost/"
# os.environ['POSTGRESQL_PASSWORD'] = ''
os.environ["SECRET_KEY"] = ""
# Note we have to set at least the above environment variables before importing our application code

from app import api, config, crud, db, models, schemas
from app.api.dependencies.security import create_user_access_token
from app.db.session import get_session
from app.models.user import User, UserAccountType
from app.services.users import generate_random_users

session = next(get_session(settings=config.get_settings()))

school = crud.school.get_by_wriveted_id_or_404(
    db=session, wriveted_id="784039ba-7eda-406d-9058-efe65f62f034"
)
print(school)

num_users = 50

for new_user in generate_random_users(
    session=session,
    num_users=num_users,
    type=UserAccountType.STUDENT,
    is_active=True,
    school_as_student=school,
):
    print(new_user)

session.commit()
print(f"Generated {num_users} new users to database")

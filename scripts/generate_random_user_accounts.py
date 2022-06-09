# Ensure your environment variables are set such that this script can connect
# directly to the database. E.g. there are different postgres passwords if running
# via docker-compose versus a Cloud SQL database.
import os

from app.schemas.class_group import ClassGroupCreateIn

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

school_id = "784039ba-7eda-406d-9058-efe65f62f034"
school = crud.school.get_by_wriveted_id_or_404(db=session, wriveted_id=school_id)
print(school)

current_classes = crud.class_group.get_all_with_optional_filters(session, school=school)
print(current_classes)

if len(current_classes) < 3:
    crud.class_group.create(
        db=session,
        obj_in=ClassGroupCreateIn(
            school_id=school_id, name=f"Test Class {len(current_classes)}"
        ),
    )

num_users = 3

for new_user in generate_random_users(
    session=session,
    num_users=num_users,
    school_id=school.id,
    first_name="Test",
    last_name_initial="U",
    type=UserAccountType.STUDENT,
    is_active=True,
    class_group_id=current_classes[-1].id,
):
    print(new_user)

session.commit()
print(f"Generated {num_users} new users to database")

# Ensure your environment variables are set such that this script can connect
# directly to the database. E.g. if running via docker-compose
import os
from typing import Optional

from sqlalchemy import distinct, select
from sqlalchemy.orm import aliased

from app.models import (
    CollectionItem,
    Edition,
    Hue,
    LabelSet,
    LabelSetHue,
    ReadingAbility,
    Work,
)
from app.services.recommendations import get_recommended_labelset_query

os.environ["POSTGRESQL_SERVER"] = "localhost/"
# os.environ['POSTGRESQL_PASSWORD'] = ''
os.environ["SECRET_KEY"] = "CHrUJmNw1haKVSorf3ooW-D6eRooePyo-V8II--We78"

# Note we have to set at least the above environment variables before importing our application code

import logging

from app import api, config, crud, db, models, schemas
from app.db.session import get_session

logging.basicConfig()
# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

session = next(get_session(settings=config.get_settings()))


labelset_query = get_recommended_labelset_query(
    session,
    school_id=None,  # 9929,
    hues=["hue05_funny_comic", "hue09_charming_playful"],
    age=None,  # 11
    reading_ability=None,  #'SPOT'
)

print("Recommendations:")
for res in session.execute(labelset_query.limit(5)).all():
    print(res)

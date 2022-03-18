# Ensure your environment variables are set such that this script can connect
# directly to the database. E.g. if running via docker-compose
import csv
import os
from typing import Optional

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import aliased

from app.api.recommendations import get_recommended_editions_and_labelsets
from app.models import (
    BookList,
    CollectionItem,
    Edition,
    Hue,
    LabelSet,
    LabelSetHue,
    ReadingAbility,
    Work,
)
from app.models.booklist import ListType
from app.schemas.recommendations import ReadingAbilityKey

os.environ["POSTGRESQL_SERVER"] = "localhost/"
# os.environ['POSTGRESQL_PASSWORD'] = ''
# os.environ["SECRET_KEY"] = ""

# Note we have to set at least the above environment variables before importing our application code

from app import crud, api, db, models, schemas
from app import config
from app.db.session import get_session

import logging

logging.basicConfig()
# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

session = next(get_session(settings=config.get_settings()))

works_for_booklist = []

huey_picks_data = csv.reader(open("HueysPicks.csv", "rt"))
next(huey_picks_data)
for i, line in enumerate(huey_picks_data):
    # print(line)
    title, isbns_str, author, scoutPicks = line

    isbns = isbns_str.split(",")

    editions = (
        session.execute(crud.edition.get_multi_query(db=session, ids=isbns))
        .scalars()
        .all()
    )

    for edition in editions:
        if (
            edition is not None
            and edition.work is not None
            and edition.work not in works_for_booklist
        ):
            works_for_booklist.append(edition.work)
            print(edition.work)

    # if i > 10:
    #     break

print(f"Found {len(works_for_booklist)} hydrated books")

booklist_orm = BookList(
    name="Huey's Picks", type=ListType.HUEY_LIST, info={}, works=works_for_booklist
)
session.add(booklist_orm)
session.commit()

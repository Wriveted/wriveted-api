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
    BookListItem,
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

booklist_items_by_work_id = {}

huey_picks_data = csv.reader(open("HueysPicks.csv", "rt"))
next(huey_picks_data)
for i, line in enumerate(huey_picks_data):
    # print(line)
    title, isbns_str, author, scoutPicks = line

    isbns = isbns_str.split(",")

    editions = session.scalars(crud.edition.get_multi_query(db=session, ids=isbns))

    for edition in editions:
        if (
            edition is not None
            and edition.work is not None
            and edition.work_id not in booklist_items_by_work_id
        ):
            book_list_item = BookListItem(
                work_id=edition.work_id,
                order_id=len(booklist_items_by_work_id),
                info={"edition": edition.isbn},
            )
            booklist_items_by_work_id[edition.work_id] = book_list_item

            print(edition.work)

    if i > 10:
        break

print(f"Found {len(booklist_items_by_work_id)} hydrated books")

booklist_orm = BookList(
    name="Huey's Picks",
    type=ListType.HUEY,
    info={},
    items=list(booklist_items_by_work_id.values()),
)
session.add(booklist_orm)
session.commit()

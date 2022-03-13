from typing import Optional

from fastapi import APIRouter, Depends, BackgroundTasks, Query
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud

from app.api.dependencies.security import get_current_active_user_or_service_account
from app.config import get_settings
from app.db.explain import explain
from app.db.session import get_session
from app.models import School
from app.schemas.labelset import LabelSetDetail

from app.schemas.recommendations import HueyBook, HueyOutput, HueyRecommendationFilter
from app.services.events import create_event

from app.services.recommendations import get_recommended_labelset_query

router = APIRouter(
    tags=["Recommendations"],
    dependencies=[Depends(get_current_active_user_or_service_account)],
)
logger = get_logger()
config = get_settings()


@router.post("/recommend", response_model=HueyOutput)
async def get_recommendations(
    data: HueyRecommendationFilter,
    background_tasks: BackgroundTasks,
    limit: Optional[int] = Query(5, description="Maximum number of items to return"),
    account=Depends(get_current_active_user_or_service_account),
    session: Session = Depends(get_session),
):
    """
    Fetch labeled works as recommended by Huey.

    Note this endpoint returns recommendations in a random order.
    """
    logger.info("Recommendation endpoint called", parameters=data)
    hues = data.hues
    age = data.age
    reading_ability = data.reading_ability

    if data.wriveted_identifier is not None:
        school = crud.school.get_by_wriveted_id_or_404(
            db=session, wriveted_id=data.wriveted_identifier
        )
        # TODO check account is allowed to `read` school
    else:
        school = None

    row_results, query_parameters = await get_recommendations_with_fallback(
        session,
        account,
        hues,
        reading_ability,
        school,
        age,
        background_tasks=background_tasks,
        limit=limit
    )
    return HueyOutput(
        count=len(row_results),
        query=query_parameters,
        books=[
            HueyBook(
                work_id=work.id,
                isbn=edition.isbn,
                cover_url=edition.cover_url,
                display_title=edition.title,
                authors_string=work.get_authors_string(),
                summary=labelset.huey_summary,
                labels=LabelSetDetail.from_orm(labelset)
            )
            for (work, edition, labelset) in row_results
        ],
    )


async def get_recommendations_with_fallback(
    session,
    account,
    hues,
    reading_ability,
    school: School,
    age: int,
    background_tasks: BackgroundTasks,
    limit=5,
):
    school_id = school.id if school is not None else None
    query_parameters = {
        "school_id": school_id,
        "hues": hues,
        "reading_ability": reading_ability,
        "age": age,
        "limit": limit,
    }
    logger.info("About to make a recommendation", query_parameters=query_parameters)
    row_results = get_recommended_editions_and_labelsets(session, **query_parameters)

    if len(row_results) < 3:
        # proper fallback logic can come later when booklists are implemented
        query_parameters["school_id"] = None
        logger.info(
            f"Desired query returned {len(row_results)} books. Trying fallback method 1 of looking outside school collection",
            query_parameters=query_parameters,
        )

        row_results = get_recommended_editions_and_labelsets(
            session, **query_parameters
        )
        if len(row_results) < 3:
            # Still not enough, alright let's recommend outside the school collection

            # Lets just include all the hues and try the query again.
            query_parameters["hues"] = None
            logger.info(
                f"Desired query returned {len(row_results)} books. Trying fallback method 2 of including all hues",
                query_parameters=query_parameters,
            )
            row_results = get_recommended_editions_and_labelsets(
                session, **query_parameters
            )

    if len(row_results) > 1:
        logged_labelset_description = "\n".join(str(b[2]) for b in row_results)

        background_tasks.add_task(
            create_event,
            session,
            title=f"Made a recommendation of {len(row_results)} books",
            description=f"Recommended:\n{logged_labelset_description}" if len(row_results) <= 10 else "",
            school=school,
            account=account,
        )
    else:
        if len(row_results) == 0:
            background_tasks.add_task(
                create_event,
                session,
                title="No books",
                description="No books met the criteria for recommendation",
                school=school,
                account=account,
            )
    return row_results, query_parameters


def get_recommended_editions_and_labelsets(
    session, school_id, hues, reading_ability, age, limit=5
):
    query = get_recommended_labelset_query(
        session,
        hues=hues,
        school_id=school_id,
        age=age,
        reading_ability=reading_ability,
    )

    if config.DEBUG:
        explain_results = session.execute(explain(query, analyze=True)).scalars().all()
        logger.info("Query plan")
        for entry in explain_results:
            logger.info(entry)

    row_results = session.execute(query.limit(limit)).all()
    return row_results

from sqlalchemy import String, cast, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from structlog import get_logger

from app.models import Author, Series, Work
from app.models.author_work_association import author_work_association_table
from app.models.search_view import search_view_v1
from app.models.series_works_association import series_works_association_table
from app.models.work_collection_frequency import work_collection_frequency
from app.schemas.author import AuthorBrief
from app.schemas.work import WorkBrief, WorkType

logger = get_logger()
author = aliased(Author)
series = aliased(Series)
awa = author_work_association_table
swa = series_works_association_table
cf = work_collection_frequency


async def book_search(
    session: AsyncSession,
    pagination,
    query_param: str | None = None,
    author_id: int = None,
) -> list[WorkBrief]:
    # Constructing the query
    highlight_config = 'StartSel="<b>", StopSel = "</b>"'

    stmt = (
        select(
            Work.id.label("work_id"),
            Work.leading_article.label("leading_article"),
            # series.id,
            func.json_agg(
                func.json_build_object(
                    "id",
                    cast(author.id, String),
                    "first_name",
                    author.first_name,
                    "last_name",
                    author.last_name,
                )
            ).label("authors"),
            func.ts_headline(
                "english",
                func.coalesce(Work.title, ""),
                func.plainto_tsquery("english", query_param),
                highlight_config,
            ).label("title"),
            func.ts_headline(
                "english",
                func.coalesce(Work.subtitle, ""),
                func.plainto_tsquery("english", query_param),
                highlight_config,
            ).label("subtitle"),
            # func.ts_headline(
            #     "english",
            #     func.coalesce(series.title, ""),
            #     func.plainto_tsquery("english", query_param),
            #     highlight_config,
            # ).label("series_title_headline"),
            (
                func.ts_rank(
                    search_view_v1.c.document,
                    func.websearch_to_tsquery("english", query_param),
                )
                * func.log(1 + func.coalesce(cf.c.collection_frequency, 0))
            ).label("rank"),
        )
        .select_from(
            search_view_v1.join(Work, Work.id == search_view_v1.c.work_id)
            .join(cf, cf.c.work_id == Work.id)
            .join(awa, awa.c.work_id == Work.id)
            .join(author, author.id == awa.c.author_id)
            # .outerjoin(swa, swa.c.work_id == Work.id)
            # .outerjoin(series, series.id == swa.c.series_id)
        )
        .where(
            search_view_v1.c.document.op("@@")(
                func.websearch_to_tsquery("english", query_param)
            )
        )
        .group_by(Work.id, search_view_v1.c.document, cf.c.collection_frequency)
        .order_by(text("rank DESC"))
    )

    if author_id is not None:
        stmt = stmt.where(author.id == author_id)

    # pagination
    stmt = (
        stmt
        # .offset(pagination.skip)
        .limit(pagination.limit)
    )

    # TODO filter by type, provided author id, etc.

    res = (await session.execute(stmt)).fetchall()

    logger.info("Result of search", res=res)

    return [
        WorkBrief(
            id=str(row[0]),
            leading_article=row[1],
            type=WorkType.BOOK,
            authors=[
                AuthorBrief.model_validate(a) if a is not None else None for a in row[2]
            ],
            title=row[3],
            subtitle=row[4],
        )
        for row in res
    ]

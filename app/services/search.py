from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from structlog import get_logger

from app.models import Author, Series, Work
from app.models.author_work_association import author_work_association_table
from app.models.search_view import search_view_v1
from app.models.series_works_association import series_works_association_table
from app.schemas.search_results import BookSearchResult

logger = get_logger()
author = aliased(Author)
series = aliased(Series)
awa = author_work_association_table
swa = series_works_association_table


async def book_search(
    session: AsyncSession, query_param: str, pagination
) -> list[BookSearchResult]:
    # Constructing the query
    stmt = (
        select(
            Work.id,
            search_view_v1.c.author_ids,
            series.id,
            func.ts_headline(
                "english",
                func.coalesce(Work.title, ""),
                func.plainto_tsquery("english", query_param),
            ).label("title_headline"),
            func.ts_headline(
                "english",
                func.coalesce(Work.subtitle, ""),
                func.plainto_tsquery("english", query_param),
            ).label("subtitle_headline"),
            func.ts_headline(
                "english",
                func.coalesce(author.first_name, ""),
                func.plainto_tsquery("english", query_param),
            ).label("first_name_headline"),
            func.ts_headline(
                "english",
                func.coalesce(author.last_name, ""),
                func.plainto_tsquery("english", query_param),
            ).label("last_name_headline"),
            func.ts_headline(
                "english",
                func.coalesce(series.title, ""),
                func.plainto_tsquery("english", query_param),
            ).label("series_title_headline"),
            func.ts_rank(
                search_view_v1.c.document,
                func.websearch_to_tsquery("english", query_param),
            ).label("rank"),
        )
        .select_from(
            search_view_v1.join(Work, Work.id == search_view_v1.c.work_id)
            .join(awa, awa.c.work_id == Work.id)
            .join(author, author.id == awa.c.author_id)
            .outerjoin(swa, swa.c.work_id == Work.id)
            .outerjoin(series, series.id == swa.c.series_id)
        )
        .where(
            search_view_v1.c.document.op("@@")(
                func.websearch_to_tsquery("english", query_param)
            )
        )
        .order_by(text("rank DESC"))
        .limit(pagination.limit)
    )

    # TODO pagination
    # TODO filter by type, provided author id, etc.

    res = (await session.execute(stmt)).fetchall()

    logger.info("Result of search", res=res)

    return [
        BookSearchResult(
            work_id=str(row[0]),
            author_ids=map(str, row[1]),
            series_id=str(row[2]) if row[2] is not None else None,
            work_title_headline=row[3],
            work_subtitle_headline=row[4],
            author_first_headline=row[5],
            author_last_headline=row[6],
            series_title_headline=row[7],
        )
        for row in res
    ]

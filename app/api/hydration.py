from fastapi import APIRouter, Depends, HTTPException, Query
from structlog import get_logger

from app.api.dependencies.security import (
    get_current_active_superuser_or_backend_service_account,
)
from app.api.editions import add_edition, get_editions_to_hydrate
from app.services.background_tasks import queue_background_task
from app.services.hydration import (
    NielsenException,
    NielsenNoResultsException,
    NielsenRateException,
    NielsenServiceException,
    hydrate,
)

logger = get_logger()

router = APIRouter(
    tags=["Hydration"],
    dependencies=[Depends(get_current_active_superuser_or_backend_service_account)],
)


@router.post("/hydrate")
async def hydrate_bulk(
    limit: int = 5000,
    isbns_to_hydrate: list[str] = [],
):
    """
    Asynchronously hydrates list of ISBNs against collated metadata sources, before sending the enriched data back to the Wriveted API.
    If no list is provided, will fetch and hydrate `limit` of the most popular unhydrated ISBNs in Wriveted db instead.
    Requires a Wriveted superuser auth token.
    """

    if not isbns_to_hydrate:
        isbns_to_hydrate = get_editions_to_hydrate(limit)

    queue_background_task(
        "hydrate-bulk",
        isbns_to_hydrate,
    )

    return (
        f"Started hydration of {len(isbns_to_hydrate)} editions. "
        "Check the logs (https://console.cloud.google.com/run/detail/australia-southeast1/wriveted-hydration/logs?project=wriveted-api) "
        "and events (https://api.wriveted.com/events/) to track progress."
    )


@router.get("/hydrate/{isbn}")
async def hydrate_single(
    isbn: str,
    use_cache: bool = Query(
        False,
        description="Return cached data if available. If false, will fetch newest data from the source, updating the cache as well.",
    ),
    dry: bool = Query(
        True,
        description="Return the data without saving it to the Wriveted db.",
    ),
):
    """
    Synchronously retrieves metadata for a single ISBN from collated metadata sources, returning the enriched data.
    Optionally stores the result in the Wriveted db.
    Requires a Wriveted superuser auth token.
    """
    try:
        data = hydrate(isbn, use_cache)
    except NielsenServiceException:
        raise HTTPException(status_code=503, detail="Nielsen API is unavailable")
    except NielsenRateException:
        raise HTTPException(status_code=429, detail="Nielsen API rate limit reached")
    except NielsenNoResultsException:
        raise HTTPException(status_code=404, detail="No results found")
    except NielsenException:
        raise HTTPException(
            status_code=503, detail="Something went wrong with the Nielsen API"
        )

    if not dry:
        add_edition(data)

    return data

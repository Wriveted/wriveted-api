import json
from typing import Any

import httpx
from google.cloud import tasks_v2
from structlog import get_logger

from app.config import get_settings

settings = get_settings()
logger = get_logger()


def queue_background_task(endpoint: str, payload: Any = None):
    url = f"{settings.WRIVETED_INTERNAL_API}v1/{endpoint}"

    if settings.GCP_CLOUD_TASKS_NAME is None:
        logger.warning("Calling internal API directly", url=url)
        return httpx.post(url, json=payload, timeout=120)
    else:
        client = tasks_v2.CloudTasksClient()
        project = settings.GCP_PROJECT_ID
        queue = settings.GCP_CLOUD_TASKS_NAME
        location = settings.GCP_LOCATION
        audience = f"{settings.WRIVETED_INTERNAL_API}/{endpoint}"
        service_account_email = settings.GCP_CLOUD_TASKS_SERVICE_ACCOUNT

        logger.info(
            "Queueing a background task",
            url=url,
            project=project,
            queue=queue,
            location=location,
            audience=audience,
            service_account_email=service_account_email,
        )

        # Construct the fully qualified queue name.
        parent = client.queue_path(project, location, queue)

        # Construct the request body.
        task = {
            "http_request": {  # Specify the type of request.
                "http_method": tasks_v2.HttpMethod.POST,
                "url": url,  # The full url path that the task will be sent to.
                "oidc_token": {
                    "service_account_email": service_account_email,
                    "audience": audience,
                },
            }
        }

        # Convert payload to bytes and add to request
        if payload is not None:
            payload = json.dumps(payload).encode()
            task["http_request"]["body"] = payload

        response = client.create_task(request={"parent": parent, "task": task})

        logger.info("Queued background task {}".format(response.name))
        return response

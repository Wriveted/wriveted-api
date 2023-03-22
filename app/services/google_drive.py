from googleapiclient.discovery import build
from structlog import get_logger

logger = get_logger()


def get_labeling_prompt_from_drive(prompt_document_id: str = None):
    service = build("drive", "v3")
    if prompt_document_id is None:
        logger.debug("Fetching default prompt from Google Drive")
        prompt_document_id = "13jFCrp0hVeRWGneh1NLicJM_-mK92495IohR_kEXnEo"
    else:
        logger.warning(
            "Fetching custom prompt from Google Drive",
            prompt_document_id=prompt_document_id,
        )

    content = (
        service.files()
        .export(fileId=prompt_document_id, mimeType="text/plain")
        .execute()
    )
    prompt = content.decode("utf-8")
    return prompt

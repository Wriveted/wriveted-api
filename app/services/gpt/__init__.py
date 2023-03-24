import json
from statistics import median
from textwrap import dedent
import time

import openai
from pydantic import ValidationError
from structlog import get_logger

from app.config import get_settings
from app.models.work import Work
from app.schemas.gpt import (
    GptLabelResponse,
    GptPromptResponse,
    GptPromptUsage,
    GptUsage,
    GptWorkData,
)
from app.services.gpt.prompt import (
    suffix,
    system_prompt,
    user_prompt_template,
    retry_prompt_template,
)

logger = get_logger()
settings = get_settings()


def gpt_query(system_prompt, user_content):
    openai.api_key = settings.OPENAI_API_KEY

    start_time = time.time()
    response = openai.ChatCompletion.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0,
        timeout=settings.OPENAI_TIMEOUT,
    )
    end_time = time.time()
    duration = end_time - start_time

    return GptPromptResponse(
        usage=GptPromptUsage(**response["usage"], duration=duration),
        output=response["choices"][0]["message"]["content"].strip(),
    )


def extract_labels(work: Work, prompt: str = None, retries: int = 2):
    target_prompt = prompt or system_prompt
    all_usages = []

    logger.info("Requesting completion from OpenAI", work_id=work.id)
    # TODO: Get a better list of related editions. E.g levenstein distance to title, largest info blobs or biggest delta in info blob content etc
    editions = [
        ed
        for ed in work.editions[:20]
        if ed.info is not None and ed.title == work.title
    ]
    editions.sort(key=lambda e: len(e.info), reverse=True)

    if not editions:
        raise ValueError("Insufficient edition data to generate labels")

    main_edition = editions[0]

    huey_summary = work.labelset.huey_summary if work.labelset else ""

    genre_data = set()
    short_summaries = set()
    page_numbers = set()

    for e in editions[:20]:
        for g in e.info.get("genres", []):
            genre_data.add(f"{g['name']}")

        short_summaries.add(e.info.get("summary_short"))

        if pages := e.info.get("pages"):
            page_numbers.add(pages)

    genre_data = "\n".join(genre_data)
    median_page_number = median(page_numbers)
    short_summaries = "\n".join(f"- {s}" for s in short_summaries if s is not None)

    display_title = work.get_display_title()
    authors_string = work.get_authors_string()
    long_summary = main_edition.info.get("summary_long", "") or ""
    keywords = main_edition.info.get("keywords", "") or ""
    other_info = dedent(
        f"""
    - {main_edition.info.get('cbmctext')}
    - {main_edition.info.get('prodct')}
    """
    )
    user_provided_values = {
        "display_title": display_title,
        "authors_string": authors_string,
        "huey_summary": huey_summary[:1500],
        "short_summaries": short_summaries[:1500],
        "long_summary": long_summary[:1500],
        "keywords": keywords[:1500],
        "other_info": other_info,
        "number_of_pages": median_page_number,
        "genre_data": genre_data[:1500],
    }
    user_content = user_prompt_template.format(**user_provided_values) + suffix

    logger.debug("User prompt prepared, sending to OpenAI...")
    gpt_response = gpt_query(target_prompt, user_content)
    all_usages.append(gpt_response.usage)

    # validate the formatting of the response
    json_data = None
    parsed_data = None
    while True:
        try:
            json_data = json.loads(gpt_response.output)
            parsed_data = GptWorkData(**json_data)
            break
        except (ValidationError, ValueError) as e:
            logger.warning(
                f"GPT response was not valid, {'retrying...' if retries > 0 else 'not retrying'}",
                work_id=work.id,
            )
            # tell gpt what is going on
            new_content = retry_prompt_template.format(
                user_content=user_content,
                response_string=gpt_response.output,
                error_message=str(e),
            )
            gpt_response = gpt_query(target_prompt, new_content)
            all_usages.append(gpt_response.usage)

        if retries <= 0:
            break

    # check if the response is valid at this point
    if not json_data or not parsed_data:
        logger.error("GPT response was not valid", work_id=work.id)
        raise ValueError("GPT response was not valid", raw=gpt_response.output)

    return GptLabelResponse(
        system_prompt=system_prompt,
        user_content=user_content,
        output=parsed_data,
        usage=GptUsage(usages=all_usages),
    )

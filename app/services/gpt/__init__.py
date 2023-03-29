import json
import time
from statistics import median
from textwrap import dedent

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
    retry_prompt_template,
    suffix,
    system_prompt,
    user_prompt_template,
)

logger = get_logger()
settings = get_settings()


def gpt_query(system_prompt, user_content, ai_content=None):
    openai.api_key = settings.OPENAI_API_KEY

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    if ai_content:
        messages.append({"role": "ai", "content": ai_content})

    logger.info("Prompts prepared, sending to OpenAI...")

    start_time = time.time()
    response = openai.ChatCompletion.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        temperature=0,
        timeout=settings.OPENAI_TIMEOUT,
    )
    end_time = time.time()
    duration = end_time - start_time

    logger.debug(f"OpenAI responded after {duration}s")

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

    huey_summary = (
        work.labelset.huey_summary
        if work.labelset and work.labelset.huey_summary
        else ""
    )

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
    median_page_number = median(page_numbers) if page_numbers else "unknown"
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

    logger.info("Prompt: ", prompt=user_content)

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
            retries -= 1
            error_string = str(e)

            if isinstance(e, ValidationError):
                # pydantic. extract the error(s) in more reasonable verbosity
                error_string = str([str(error.exc) for error in e.raw_errors])

            logger.warning(
                "GPT response was not valid",
                output=gpt_response.output,
                error=error_string,
                retrying=retries > 0,
                work_id=work.id,
            )

            # tell gpt what is going on
            ai_content = gpt_response.output
            new_content = retry_prompt_template.format(
                user_content=user_content,
                error_message=error_string,
            )
            gpt_response = gpt_query(target_prompt, new_content, ai_content)
            all_usages.append(gpt_response.usage)

        if retries <= 0:
            break

    # check if the response is valid at this point
    if not json_data or not parsed_data:
        raise ValueError

    usage = GptUsage(usages=all_usages)
    logger.info("GPT response was valid", work_id=work.id, usage=usage)

    logger.debug("GPT response", response=gpt_response.output)

    return GptLabelResponse(
        system_prompt=system_prompt,
        user_content=user_content,
        output=parsed_data,
        usage=GptUsage(usages=all_usages),
    )

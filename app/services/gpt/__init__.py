import json
import time
from statistics import median
from textwrap import dedent

import openai
from pydantic import ValidationError
from structlog import get_logger

import app.api.works
from app import crud
from app.config import get_settings
from app.models.labelset import LabelOrigin
from app.models.work import Work
from app.schemas.gpt import (
    GptLabelResponse,
    GptPromptResponse,
    GptPromptUsage,
    GptUsage,
    GptWorkData,
)
from app.schemas.labelset import LabelSetCreateIn
from app.schemas.work import WorkUpdateIn
from app.services.gpt.prompt import (
    retry_prompt_template,
    suffix,
    system_prompt,
    user_prompt_template,
)

logger = get_logger()
settings = get_settings()


def gpt_query(system_prompt, user_content, extra_messages=None):
    openai.api_key = settings.OPENAI_API_KEY

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    if extra_messages:
        messages.extend(extra_messages)

    logger.debug("Prompts prepared, sending to OpenAI...")

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

    logger.debug("Requesting completion from OpenAI", work_id=work.id)
    # TODO: Get a better list of related editions. E.g levenstein distance to title, largest info blobs or biggest delta in info blob content etc
    editions = [
        ed
        for ed in work.editions[:20]
        if ed.info is not None and ed.title == work.title
    ]
    editions.sort(key=lambda e: len(e.info), reverse=True)

    if not editions:
        logger.warning("Insufficient edition data to generate good labels")
        main_edition = work.editions[0]
    else:
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

            logger.warning(
                "GPT response was not valid",
                output=gpt_response.output,
                error=error_string,
                retrying=retries > 0,
                work_id=work.id,
            )

            # try again, provide new gpt thread with full context
            ai_response = {"role": "assistant", "content": gpt_response.output}
            validation_response = {
                "role": "user",
                "content": retry_prompt_template.format(
                    user_content=user_content,
                    error_message=error_string,
                ),
            }
            gpt_response = gpt_query(
                target_prompt,
                user_content,
                extra_messages=[ai_response, validation_response],
            )
            all_usages.append(gpt_response.usage)

        if retries <= 0:
            break

    # check if the response is valid at this point
    if not json_data:
        raise ValueError("GPT response was not valid JSON after exhausting retries")
    elif not parsed_data:
        raise ValueError(
            "GPT response was not valid GPTLabelResponse after exhausting retries"
        )

    usage = GptUsage(usages=all_usages)
    logger.info("GPT response was valid", work_id=work.id, usage=usage)

    logger.debug("GPT response", response=gpt_response.output)

    return GptLabelResponse(
        system_prompt=system_prompt,
        user_content=user_content,
        output=parsed_data,
        usage=GptUsage(usages=all_usages),
    )


def work_to_gpt_labelset_update(work: Work):
    gpt_data = extract_labels(work, retries=2)

    output = gpt_data.output

    labelset_data = {}

    # reading abilities
    labelset_data["reading_ability_keys"] = output.reading_ability
    labelset_data["reading_ability_origin"] = LabelOrigin.GPT4

    # hues
    if output.hues:
        labelset_data["hue_primary_key"] = output.hues[0]
    if len(output.hues) > 1:
        labelset_data["hue_secondary_key"] = output.hues[1]
    if len(output.hues) > 2:
        labelset_data["hue_tertiary_key"] = output.hues[2]
    labelset_data["hue_origin"] = LabelOrigin.GPT4

    # summary
    labelset_data["huey_summary"] = output.short_summary
    labelset_data["summary_origin"] = LabelOrigin.GPT4

    # other
    labelset_info = {}
    labelset_info["long_summary"] = output.long_summary
    labelset_info["genres"] = output.genres
    labelset_info["styles"] = output.styles
    labelset_info["characters"] = output.characters
    labelset_info["hue_map"] = output.hue_map
    labelset_info["series"] = output.series
    labelset_info["series_number"] = output.series_number
    labelset_info["gender"] = output.gender
    labelset_info["awards"] = output.awards
    labelset_info["notes"] = output.notes
    labelset_info["controversial_themes"] = output.controversial_themes

    labelset_data["info"] = labelset_info

    # mark as needing to be checked
    labelset_data["checked"] = None

    labelset_data["recommend_status"] = output.recommend_status
    labelset_data["recommend_status_origin"] = LabelOrigin.GPT4

    labelset_create = LabelSetCreateIn(**labelset_data)
    return labelset_create


async def label_and_update_work(work: Work, session):
    labelset_update = work_to_gpt_labelset_update(work)
    changes = WorkUpdateIn(labelset=labelset_update)

    gpt = crud.service_account.get_or_404(
        db=session, id=settings.GPT_SERVICE_ACCOUNT_ID
    )

    await app.api.works.update_work(
        changes=changes, work_orm=work, account=gpt, session=session
    )
    logger.info(f"Updated labelset for {work.title}")

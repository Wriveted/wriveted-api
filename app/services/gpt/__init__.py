import json
from statistics import median
from textwrap import dedent

import openai

from app.config import get_settings
from app.models.work import Work
from app.services.gpt.prompt import system_prompt, user_prompt_template

settings = get_settings()


def extract_labels(work: Work, prompt: str = None):
    editions = [
        ed
        for ed in work.editions[:20]
        if ed.info is not None and ed.title == work.title
    ]
    main_edition = editions[0]

    huey_summary = work.labelset.huey_summary

    genre_data = set()
    for e in editions[:20]:
        for g in e.info.get("genres", []):
            genre_data.add(f"{g['source']};{g['name']}")
    genre_data = "\n".join(genre_data)

    short_summaries = set()
    for e in editions:
        short_summaries.add(e.info.get("summary_short"))

    page_numbers = set()
    for e in editions:
        if pages := e.info.get("pages"):
            page_numbers.add(pages)
    median_page_number = median(page_numbers)

    short_summaries = "\n".join(f"- {s}" for s in short_summaries if s is not None)

    display_title = work.get_display_title()
    authors_string = work.get_authors_string()
    long_summary = main_edition.info.get("summary_long")
    keywords = main_edition.info.get("keywords")
    other_info = dedent(
        f"""
    - {main_edition.info.get('cbmctext')}
    - {main_edition.info.get('prodct')}
    """
    )

    user_content = user_prompt_template.format(
        display_title=display_title,
        authors_string=authors_string,
        huey_summary=huey_summary,
        short_summaries=short_summaries,
        long_summary=long_summary,
        keywords=keywords,
        other_info=other_info,
        number_of_pages=median_page_number,
        genre_data=genre_data,
    )

    openai.api_key = settings.OPENAI_API_KEY

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": prompt or system_prompt},
            {"role": "user", "content": user_content},
            # {"role": "assistant", "content": "Who's there?"},
            # {"role": "user", "content": "Orange."},
        ],
        temperature=0,
    )

    # print(response['usage']['total_tokens'])
    # print(response['choices'][0]['message']['content'])

    try:
        response_string = response["choices"][0]["message"]["content"].strip()
        # response_string = response_string.replace("\n", "").replace("'", '"')
        # Try to parse the response string as JSON
        json_data = json.loads(response_string)
    except ValueError:
        # If the response string is not valid JSON, try to extract the JSON string
        try:
            json_start = response_string.index("{")
            json_end = response_string.rindex("}") + 1
            json_data = json.loads(response_string[json_start:json_end])
        except ValueError:
            json_data = {"error": "Could not parse JSON", "response": response_string}

    return {
        "system_prompt": prompt or system_prompt,
        "user_content": user_content,
        "output": json_data,
        "usage": response["usage"],
    }

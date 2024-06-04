from typing import List

import vertexai
from langchain_core.messages import HumanMessage, SystemMessage

# from vertexai.generative_models import GenerativeModel, Part
from langchain_google_vertexai import ChatVertexAI
from rich import print
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import database_connection
from app.models import Edition, Work
from app.services.gpt import (
    extract_labels,
    prepare_context_for_labelling,
    suffix,
    system_prompt,
)

GCP_PROJECT_ID: str = "wriveted-api"
GCP_LOCATION: str = "us-central1"

settings = get_settings()

engine, SessionLocal = database_connection(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
)

from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_core.tools import Tool, tool
from langchain_google_community import GoogleSearchAPIWrapper

wikipedia = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())
search = GoogleSearchAPIWrapper(
    google_api_key=settings.GOOGLE_API_KEY,
    google_cse_id=settings.GOOGLE_CSE_ID,
)

search_tool = Tool(
    name="google_search",
    description="Search Google for recent results.",
    func=search.run,
)

# print(wikipedia.run("Harry Potter"))
# print(search_tool.run("Obama's first name?"))

vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)

llm = ChatVertexAI(model="gemini-1.5-pro-preview-0409")


#
# @tool
# def multiply(first_int: int, second_int: int) -> int:
#     """Multiply two integers together."""
#     return first_int * second_int

llm_with_tools = llm.bind_tools([search_tool, wikipedia])


def sample_editions_to_label(session, limit=10):
    q = (
        select(Edition.isbn)
        .join(Work, Edition.work_id == Work.id)
        .where(Edition.hydrated == False)
        .where(Edition.work_id != None)
        .where(Work.labelset == None)
        .order_by(Edition.collection_count.desc())
        .limit(limit)
    )
    isbns_to_hydrate = session.execute(q).scalars().all()

    editions: List[Edition] = session.scalars(
        select(Edition).where(Edition.isbn.in_(isbns_to_hydrate))
    ).all()

    return editions


with Session(engine) as session:
    print("Getting editions to label")
    editions = sample_editions_to_label(session, 2)
    print(f"Labeling {len(editions)} editions")
    total_tokens = 0

    for e in editions:
        work = e.work
        print(work)
        user_content = prepare_context_for_labelling(work)

        print("USER CONTENT")
        # print(user_content)

        # Let's carry out some searches to help the LLM
        web_search_awards = search_tool.run(
            f'Awards for "{e.title}" by {work.get_authors_string()}'
        )

        print(web_search_awards)

        user_content += "\n" + web_search_awards

        response = llm_with_tools.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=user_content)]
        )

        print(response)

    print("done")

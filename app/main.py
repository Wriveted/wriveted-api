import uuid

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_session
from app.models import Work, Author, Series, Edition

app = FastAPI()


@app.get("/")
async def root(session: Session = Depends(get_session),):
    config = get_settings()
    books = session.query(Work)
    book_data = [
        {
            "title": b.title,
            "authors": [a.full_name for a in b.authors],
            "info": b.info,
            "editions": [
                {"ISBN": e.ISBN, "cover-url": e.cover_url, "info": e.info}
                for e in b.editions]
        }
        for b in books]

    session.commit()

    return {
        "message": "Hello World",
        "config": config,
        "books": book_data
    }


@app.post("/book")
async def add_book(session: Session = Depends(get_session),):
    new_author_id = uuid.uuid4().hex[:6].lower()

    new_author = Author(
        id=new_author_id,
        first_name=uuid.uuid4().hex[:4].lower(),
        last_name="Author",

    )

    new_series = Series(
        id=uuid.uuid4().hex[:6].lower(),
        title="Harry Potter"
    )

    new_work = Work(
        id=uuid.uuid4().hex[:6].lower(),
        authors=[new_author],
        series=new_series,
        title="Harry Potter and the Prisoner of Azkaban",
        #info={}
    )

    new_edition = Edition(
        id=uuid.uuid4().hex[:6].lower(),
        ISBN="9780545582933",
        #id=uuid.uuid4().hex[:6].lower(),
        cover_url="https://static.wikia.nocookie.net/harrypotter/images/a/a8/Harry_Potter_and_the_Prisoner_of_Azkaban_2.jpg/revision/latest?cb=20130803163319",
        work=new_work
        #info={}
    )

    session.add(new_author)
    session.add(new_work)
    session.add(new_edition)
    session.commit()

    return {
        "message": "Added book to database",
        "work": new_work,
        "edition": new_edition,
        "ISBN": new_edition.ISBN
    }


@app.get("/books/{isbn}")
async def get_book(isbn: str, session: Session = Depends(get_session)):
    e = session.query(Edition).filter(Edition.ISBN == isbn)
    return {"Title": e.all()[0].work.title}


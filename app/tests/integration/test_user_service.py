import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.public_reader import PublicReader
from app.models.user import UserAccountType
from app.services.users import (
    WordList,
    WordListItem,
    generate_random_username_from_wordlist,
    new_random_username,
)


def test_generate_new_random_user_name():
    with WordList() as wordlist:
        assert isinstance(wordlist[0], WordListItem)
        output = generate_random_username_from_wordlist(
            wordlist=wordlist,
            adjective=False,
            colour=False,
            noun=True,
            numbers=0,
            slugify=False,
        )
    assert isinstance(output, str)


def test_generate_random_user_name_from_fixed_list():
    wordlist = [WordListItem(adjective="A", colour="C", noun="N")]
    output = generate_random_username_from_wordlist(
        wordlist=wordlist,
        adjective=False,
        colour=False,
        noun=True,
        numbers=0,
        slugify=False,
    )
    assert isinstance(output, str)
    assert output.startswith("N")

    output = generate_random_username_from_wordlist(
        wordlist=wordlist,
        adjective=False,
        colour=True,
        noun=True,
        numbers=0,
        slugify=False,
    )
    assert isinstance(output, str)
    assert output.startswith("CN")

    output = generate_random_username_from_wordlist(
        wordlist=wordlist,
        adjective=True,
        colour=True,
        noun=True,
        numbers=0,
        slugify=False,
    )
    assert isinstance(output, str)
    assert output == "ACN"
    output = generate_random_username_from_wordlist(
        wordlist=wordlist,
        adjective=True,
        colour=True,
        noun=True,
        numbers=2,
        slugify=False,
    )

    assert isinstance(output, str)
    assert output.startswith("ACN")
    assert output[3:].isdigit()


def test_generate_random_user_name_checks_existing_users(session):
    wordlist = [WordListItem(adjective="A", colour="C", noun="N")]

    for i in range(5):
        session.add(
            PublicReader(
                name=f"TestUser{i}",
                username=f"ACN{i}",
                email=f"ACN{i}",
                type=UserAccountType.PUBLIC,
            )
        )

    # Ensure the database has all these supposed existing users in the current transaction
    session.flush()

    # Manually check db knows about them:
    # print(session.scalars(select(User.username).where(User.username.is_not(None))).all())

    for i in range(5):
        output = new_random_username(
            session=session,
            wordlist=wordlist,
            adjective=True,
            colour=True,
            noun=True,
            numbers=1,
            slugify=False,
        )
        session.add(
            PublicReader(
                name=f"TestUser{i}",
                username=output,
                email=output,
                type=UserAccountType.PUBLIC,
            )
        )

        # Should be all fine to here - send everything to the db to check
        session.flush()

    print(
        session.scalars(
            select(PublicReader.username).where(PublicReader.username.is_not(None))
        ).all()
    )

    # Trigger impossible to satisfy demand
    with pytest.raises(ValueError):
        impossible = new_random_username(
            session=session,
            wordlist=wordlist,
            adjective=True,
            colour=True,
            noun=True,
            numbers=1,
            slugify=False,
        )

    # Finally, check that the username unique constraint is enforced:
    with pytest.raises(IntegrityError):
        session.add(
            PublicReader(
                name=f"TestUser",
                username=output,
                email="a-new-email",
                type=UserAccountType.PUBLIC,
            )
        )
        session.flush()

    session.rollback()

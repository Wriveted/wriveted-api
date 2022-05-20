from app.services.users import WordList, WordListItem, new_random_username


def test_generate_new_random_user_name(client, session):

    with WordList() as wordlist:
        assert isinstance(wordlist[0], WordListItem)
        output = new_random_username(session=session, wordlist=wordlist)

    assert isinstance(output, str)

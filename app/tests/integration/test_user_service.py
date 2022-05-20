from app.services.users import WordList, WordListItem, new_random_username


def test_generate_new_random_user_name(client, session):

    with WordList() as wordlist:
        assert isinstance(wordlist[0], WordListItem)
        output = new_random_username(session=session, wordlist=wordlist)

    assert isinstance(output, str)


def test_generate_random_user_name_from_fixed_list(client, session):
    wordlist = [WordListItem(adjective="A", colour="C", noun="N")]

    output = new_random_username(session=session, wordlist=wordlist)
    assert isinstance(output, str)
    assert output.startswith("CN")

    output = new_random_username(session=session, wordlist=wordlist, adjective=True)
    assert isinstance(output, str)
    assert output.startswith("ACN")

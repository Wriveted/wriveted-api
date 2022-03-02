import pytest
from app.services.editions import get_definitive_isbn


def test_valid_isbn10():
    valid_isbn10 = "1-40885-5658"
    get_definitive_isbn(valid_isbn10)


def test_invalid_isbn10():
    # last check digit changed
    invalid_isbn10 = "1-40885-5655"
    
    with pytest.raises(Exception):
        get_definitive_isbn(invalid_isbn10)
        

def test_valid_isbn13():
    valid_isbn13 = "978-01430-39952"
    get_definitive_isbn(valid_isbn13)


def test_invalid_isbn13():
    # last check digit changed
    invalid_isbn13 = "978-01430-39955"
    
    with pytest.raises(Exception):
        get_definitive_isbn(invalid_isbn13)


def test_non_isbn():
    # not an isbn at all
    non_isbn = "1oops2ouch3aw4cripes"
    
    with pytest.raises(Exception):
        get_definitive_isbn(non_isbn)


def test_empty():    
    with pytest.raises(Exception):
        get_definitive_isbn("")

    with pytest.raises(Exception):
        get_definitive_isbn(None)
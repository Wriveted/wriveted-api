import random

from sqlalchemy.orm import Session


def new_random_class_code(session: Session, length: int = 6):
    """
    Generates a new random class code using 6 alphanumerics*,
    ensuring it's not already claimed by a class.

    * Ambiguities such as 1/I, O/0 have been omitted, as have vowels,
    in an attempt to prevent accidental generation of any profanities.
    Final entropy: 24 ^ 6 = 191,102,976 combinations
    """
    from app import crud

    code = ""
    code_valid = False
    attempts_remaining = 1000

    while not code_valid and attempts_remaining > 0:
        code = "".join(random.choice("2346789BCDFGHJKMPQRTVWXY") for i in range(length))
        code_valid = code and crud.class_group.get_by_class_code(session, code) is None
        attempts_remaining -= 1

    if attempts_remaining == 0:
        raise ValueError("Couldn't generate a random class code")

    return code

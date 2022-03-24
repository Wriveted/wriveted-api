from app.models import School


def get_experiments(school: School) -> dict[str, bool]:

    return {
        "no-jokes": False,
        "no-choice-option": True
    }
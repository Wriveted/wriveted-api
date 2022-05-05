import csv
import json
from typing import Optional

import httpx
import jsonpickle

from app.models.labelset import LabelOrigin, RecommendStatus

READING_ABILITY_MAP = {
    "Spot": "SPOT",
    "Cat The Hat": "CAT_HAT",
    "Treehouse": "TREEHOUSE",
    "Charlie and The Chocolate Factory": "CHARLIE_CHOCOLATE",
    "Harry Potter": "HARRY_POTTER",
}


class LabelSetCreateIn:
    hue_primary_key: Optional[str]
    hue_secondary_key: Optional[str]
    hue_tertiary_key: Optional[str]
    hue_origin: Optional[LabelOrigin]
    min_age: Optional[int]
    max_age: Optional[int]
    age_origin: Optional[LabelOrigin]
    reading_ability_keys: Optional[list[str]]
    reading_ability_origin: Optional[LabelOrigin]
    huey_summary: Optional[str]
    summary_origin: Optional[LabelOrigin]
    info: Optional[dict]
    recommend_status: Optional[RecommendStatus]
    recommend_status_origin: Optional[LabelOrigin]
    checked: Optional[bool]


class LabelSetPatch:
    isbn: str
    patch_data: LabelSetCreateIn
    huey_pick: bool

    def __init__(self, isbn, patch_data, huey_pick):
        self.isbn = isbn
        self.patch_data = patch_data
        self.huey_pick = huey_pick


book_data = []

with open("C:/ingest-mar7.csv", encoding="utf-8-sig") as csvf:
    csvReader = csv.DictReader(csvf, skipinitialspace=True)
    book_data = [{k: v for k, v in row.items()} for row in csvReader]

# labelset data, plus HueyPicks boolean
cleaned_data: list[LabelSetPatch] = []

for book in book_data:
    isbn = book["ISBN13"]
    cleaned = LabelSetCreateIn()
    huey_pick = False

    # age
    age_tags = [int(a) for a in book["Age_TAG"].split(",") if a and a.isnumeric]
    min_str = book["Min Age"]
    try:
        cleaned.min_age = int(book["Min Age"])
    except:
        cleaned.min_age = min(age_tags, default=None)
    try:
        cleaned.max_age = int(book["Max Age"])
    except:
        cleaned.max_age = max(age_tags, default=None)
    if "Human" in book["Age Origin"] or min_str:
        cleaned.age_origin = LabelOrigin.HUMAN.name
    else:
        cleaned.age_origin = LabelOrigin.PREDICTED_NIELSEN.name

    # reading abilities
    reading_abilities = book["reading_ability"].split(",")
    cleaned.reading_ability_keys = []
    for ra in reading_abilities:
        try:
            cleaned.reading_ability_keys.append(READING_ABILITY_MAP[ra])
        except KeyError:
            continue

    if cleaned.reading_ability_keys:
        cleaned.reading_ability_origin = (
            LabelOrigin.HUMAN.name
            if "Human" in book["Reading ability origin"]
            else LabelOrigin.PREDICTED_NIELSEN.name
        )

    # huey summary
    cleaned.huey_summary = book["Scout Summary"] if book["Scout Summary"] else None
    cleaned.summary_origin = "HUMAN" if cleaned.huey_summary else None

    # hues
    # sometimes there are multiples in `primary/secondary/tertiary, so we construct an ordered pool from which to grab a single hue for each,
    # keeping priority order. i.e. if a book has two primary hues and one secondary hue, the two primaries will now fill primary and secondary,
    # and the old secondary gets bumped to tertiary
    primary_hues = [
        h.replace("DO NOT USE hue04_charming joyful", "hue08_charming_inspiring")
        for h in book["Hue Primary"].split(",")
    ]
    secondary_hues = [
        h.replace("DO NOT USE hue04_charming joyful", "hue08_charming_inspiring")
        for h in book["Hue Secondary"].split(",")
    ]
    tertiary_hues = [
        h.replace("DO NOT USE hue04_charming joyful", "hue08_charming_inspiring")
        for h in book["Hue Tertiary"].split(",")
    ]
    available_hues = primary_hues + secondary_hues + tertiary_hues

    used_hues = set()
    first = next((h for h in available_hues if h not in used_hues and h != ""), None)
    used_hues.add(first)
    cleaned.hue_primary_key = first
    second = next((h for h in available_hues if h not in used_hues and h != ""), None)
    used_hues.add(second)
    cleaned.hue_secondary_key = second
    third = next((h for h in available_hues if h not in used_hues and h != ""), None)
    used_hues.add(third)
    cleaned.hue_tertiary_key = third

    cleaned.hue_origin = (
        LabelOrigin.HUMAN.name
        if "Human" in book["Hue origin"]
        else LabelOrigin.CLUSTER_ZAINAB.name
    )

    # genres
    try:
        cleaned.info = {}
        cleaned.info["genres"] = [
            {"name": name, "source": "HUMAN"} for name in book["Genre"].split(",")
        ]
    except:
        pass

    # checked
    try:
        cleaned.checked = int(book["Checked"][0]) > 0
    except:
        cleaned.checked = False

    try:
        huey_pick = int(book["Scouts Pick"][0]) > 0
    except:
        huey_pick = False

    cleaned_data.append(LabelSetPatch(book["ISBN13"], cleaned, huey_pick))

body = jsonpickle.encode(cleaned_data, unpicklable=False, make_refs=False)
json_body = json.loads(body)

response = httpx.patch(
    "http://localhost:8000/v1/labelsets",
    json=json_body,
    headers={
        "Authorization": f"Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2NDc3NTg3MzAsImlhdCI6MTY0NzA2NzUzMCwic3ViIjoiV3JpdmV0ZWQ6VXNlci1BY2NvdW50OjkxODRjNzY5LTU5NDctNGMyMy1iNWU0LTVlODYxMjQ4NTdmZSJ9.5kkAelJ3ZQv7AdOD7cMpiw7fW4kDr3J9AmLWb0ymJps"
    },
    timeout=120,
)
try:
    response.raise_for_status()
    print(response.json())
except Exception as ex:
    print(ex)
    print("Batch failed. Skipping...")

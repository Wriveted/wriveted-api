import html
import re
from datetime import datetime
from math import ceil, floor
from textwrap import shorten

from bs4 import BeautifulSoup
from pydantic import BaseModel, root_validator
from structlog import get_logger

from app.models.labelset import LabelOrigin, RecommendStatus
from app.schemas.edition import EditionInfo, Genre
from app.schemas.recommendations import HueKeys, ReadingAbilityKey

logger = get_logger()

# http://docplayer.net/212150627-Bookscan-product-classes.html
REFERENCE_PRODCC = [
    "Y4.2",  # reference and home learning
    "Y4.3",  # children's dictionaries
    "Y5",  # school textbooks & study guides
    "Y6",  # children's cartographic product / atlases
    "S",  # non-fiction specialist (humanities, stem, research)
    "T",  # non-fiction trade (politics, history, biography, reference, religion)
]
CONTROVERSIAL_PRODCC = [
    "F2.6",  # erotic fiction
    "T6",  # religion
    "T7",  # politics
    "T9",  # sex, pregnancy, problems/illness
    "T10",  # alternative therapy, the occult, paranomal, spirituality
]

# https://ns.editeur.org/bic_categories
REFERENCE_BIC2SC = [
    "A",  # the arts
    "B",  # biography
    "C",  # language
    "D",  # literary studies
    "E",  # english language teaching,
    "G",  # reference, information and interdisciplinary subjects
    "H",  # humanities
    "J",  # society & social studies
    "K",  # finance/economics
    "L",  # law
    "M",  # medicine,
    "P",  # mathematics,
    "R",  # earth sciences
    "T",  # technology, engineering, agriculture
    "U",  # computing and information technology (shudder)
    "V",  # health
    "W",  # lifestyle and leisure
    "YNL",  # literature, books and writers
    "YQ",  # education material
]
CONTROVERSIAL_BIC2SC = [
    "5X",  # contains explicit material,
    "YX",  # personal, sexual, social issues
    "JMU",  # sexual behaviour,
    "VFV",  # relationships, sex
]

# https://ns.editeur.org/thema/en
REFERENCE_THEMA = [
    "A",  # the arts
    "C",  # language
    "D",  # biography, literature and literary studies
    "E",  # english language teaching,
    "G",  # reference, information and interdisciplinary subjects
    "J",  # society & social studies
    "K",  # finance/economics, business
    "L",  # law
    "M",  # medicine/nursing
    "P",  # mathematics/science
    "Q",  # philosophy/religion
    "R",  # earth sciences
    "S",  # sport and outdoor recreation
    "T",  # technology, engineering, agriculture
    "U",  # computing and information technology (shudder)
    "V",  # health, relationships and personal
    "W",  # lifestyle and leisure
    "YNL",  # literature, books and writers
    "YP",  # education material
    "YR",  # reference material
    "YX",  # personal and social topics
    "YZ",  # stationery and misc
]
CONTROVERSIAL_THEMA = [
    "5P",  # relating to specific groups and cultures (religion, lgbt, social status)
    "JBF",  # social and ethical issues
    "XAMT",  # manga: yaoi
    "XAMV",  # manga: bara
    "XAMX",  # manga: adult
    "XAMY",  # manga: yuri
]

BORING_TITLES = [
    "aussie nibbles",
    "puffin nibbles",
    "aussie bites",
    "puffin bites",
    "aussie chomps",
    "puffin chomps",
]

# https://bic.org.uk/files/pdfs/Cbmctec1.pdf
CBMC_AGE_MAP = {
    "A": {"min": 0, "max": 5},
    "B": {"min": 5, "max": 7},
    "C": {"min": 7, "max": 9},
    "D": {"min": 9, "max": 11},
    "E": {"min": 12, "max": 14},
}

# https://ns.editeur.org/thema/en/5A
THEMA_AGE_MAP = {
    "5AB": {"min": 0, "max": 2},
    "5AC": {"min": 3, "max": 4},
    "5AD": {"min": 4, "max": 6},
    "5AF": {"min": 5, "max": 7},
    "5AG": {"min": 6, "max": 8},
    "5AH": {"min": 7, "max": 9},
    "5AJ": {"min": 8, "max": 10},
    "5AK": {"min": 9, "max": 11},
    "5AL": {"min": 10, "max": 12},
    "5AM": {"min": 11, "max": 13},
    "5AN": {"min": 12, "max": 14},
    "5AP": {"min": 13, "max": 15},
    "5AQ": {"min": 14, "max": 16},
    "5AS": {"min": 15, "max": 17},
    "5AT": {"min": 16, "max": 18},
    "5AU": {"min": 17, "max": 19},
}

# https://ns.editeur.org/bic_categories/3607
BIC_AGE_MAP = {
    "5AB": {"min": 0, "max": 2},
    "5AC": {"min": 3, "max": 4},
    "5AD": {"min": 4, "max": 6},
    "5AF": {"min": 5, "max": 7},
    "5AG": {"min": 6, "max": 8},
    "5AH": {"min": 7, "max": 9},
    "5AJ": {"min": 8, "max": 10},
    "5AK": {"min": 9, "max": 11},
    "5AL": {"min": 10, "max": 12},
    "5AM": {"min": 11, "max": 13},
    "5AN": {"min": 12, "max": 14},
    "5AP": {"min": 13, "max": 15},
    "5AQ": {"min": 14, "max": 16},
}


class Contributor(BaseModel):
    first_name: str | None  # ICFN
    last_name: str  # ICKN

    @root_validator(pre=True)
    def validate(cls, values):
        # in the case of a single-name author, Nielsen will use a last name only (i.e. Homer, {blank})
        # but in the case of a comapny, Nielsen will use a first name only (i.e. {blank}, Australian Geographic)
        # in such cases where only a first name is provided, use it as a last name instead (for internal consistency)
        if not values.get("last_name") and values.get("first_name"):
            values["last_name"] = values["first_name"]
            values["first_name"] = None

        return values


class EstimatedLabelSet(BaseModel):
    hues: list[HueKeys] = []
    hue_origin: LabelOrigin | None

    min_age: int | None
    max_age: int | None
    age_origin: LabelOrigin | None

    reading_abilities: list[ReadingAbilityKey] = []
    reading_ability_origin: LabelOrigin | None

    huey_summary: str | None
    summary_origin: LabelOrigin | None

    info: dict | None

    recommend_status: RecommendStatus | None
    recommend_status_origin: LabelOrigin | None


class HydratedBookData(BaseModel):
    isbn: str = None
    other_isbns: list[str] = []

    title: str | None = None  # TL
    leading_article: str | None = None  # LA
    subtitle: str | None = None  # ST

    series_name: str | None = None  # SN
    series_number: str | None = None  # NWS

    authors: list[Contributor] = []  # CNF{n} if CR{n} in ["A01", "A02"]
    illustrators: list[Contributor] = []  # CNF{n} if CR{n} in ["A12", "A35"]

    cover_url: str | None = None
    date_published: int | None = None  # PUBPD

    info: EditionInfo | None = None
    labelset: EstimatedLabelSet | None = None

    hydrated_on: datetime | None = None

    raw: dict | None = None

    @classmethod
    def from_nielsen_blob(cls, blob: dict):
        instance = cls()
        instance.raw = blob
        instance.info = EditionInfo()

        # get the basics out of the way
        instance.isbn = blob.get("ISBN13")
        instance.leading_article = blob.get("LA")
        instance.title = blob.get("TL")
        instance.subtitle = blob.get("ST")
        instance.series_name = blob.get("SN")
        instance.series_number = (
            int("".join(filter(str.isdigit, blob.get("NWS"))))
            if blob.get("NWS")
            else None
        )
        instance.info.pages = int(blob.get("PAGNUM")) if blob.get("PAGNUM") else None
        instance.date_published = int(blob.get("PUBPD")) if blob.get("PUBPD") else None
        instance.info.country = blob.get("COP")

        # nielsen's max number of instances for a given type is 10
        # iterate through all such multi-field instances
        for i in range(1, 10):
            # look for "contributors" (authors/illustrators)
            if f"CNF{i}" in blob:
                # http://www.onix-codelists.io/codelist/17
                if blob.get(f"CR{i}") in ["A01", "A02"]:
                    instance.authors.append(
                        Contributor(
                            first_name=blob.get(f"ICFN{i}"),
                            last_name=blob.get(f"ICKN{i}"),
                        )
                    )
                elif blob.get(f"CR{i}") in ["A12", "A35"]:
                    instance.illustrators.append(
                        Contributor(
                            first_name=blob.get(f"ICFN{i}"),
                            last_name=blob.get(f"ICKN{i}"),
                        )
                    )

            # look for "genres"
            if f"BISACT{i}" in blob:
                instance.info.genres.append(
                    Genre(
                        name=blob.get(f"BISACT{i}"),
                        source="BISAC",
                        code=blob.get(f"BISACC{i}"),
                    ),
                )
            if f"BIC2ST{i}" in blob:
                instance.info.genres.append(
                    Genre(
                        name=blob.get(f"BIC2ST{i}"),
                        source="BIC",
                        code=blob.get(f"BIC2SC{i}"),
                    ),
                )
            if f"THEMAST{i}" in blob:
                instance.info.genres.append(
                    Genre(
                        name=blob.get(f"THEMAST{i}"),
                        source="THEMA",
                        code=blob.get(f"THEMASC{i}"),
                    ),
                )
            if f"LOCSH{i}" in blob:
                instance.info.genres.append(
                    Genre(name=blob.get(f"LOCSH{i}"), source="LOCSH", code=None)
                )

            # look for "qualifiers" (misc. but can be useful for determining age)
            if f"BIC2QC{i}" in blob:
                instance.info.bic_qualifiers.append(blob.get(f"BIC2QC{i}"))
            if f"THEMAQC{i}" in blob:
                instance.info.thema_qualifiers.append(blob.get(f"THEMAQC{i}"))

            # look for "product content types" (includes the medium i.e. paperback/audiobook etc.)
            if f"PCTCT{i}" in blob:
                instance.info.medium_tags.append(blob.get(f"PCTCT{i}"))

        instance.info.prodcc = blob.get("PRODCC")
        instance.info.prodct = blob.get("PRODCT")
        instance.info.cbmccode = blob.get("CBMCCODE")
        instance.info.cbmctext = blob.get("CBMCTEXT")
        if "PFCT" in blob:
            instance.info.medium_tags.append(blob.get("PFCT"))

        # short summary good for landbot, long summary good for generating hues (or as a backup)
        # sometimes contain encoded html in the string, which we don't need
        instance.info.summary_short = blob.get("AUSFSD")
        if instance.info.summary_short:
            instance.info.summary_short = (
                BeautifulSoup(
                    html.unescape(instance.info.summary_short), features="html.parser"
                )
                .get_text()
                .replace("\t", "")
                .replace("\r", "")
                .replace("\n", "")
                .replace("nbsp;", "")
                .strip()
            )
        instance.info.summary_long = blob.get("AUSFLD")
        if instance.info.summary_long:
            instance.info.summary_long = (
                BeautifulSoup(
                    html.unescape(instance.info.summary_long), features="html.parser"
                )
                .get_text()
                .replace("\t", "")
                .replace("\r", "")
                .replace("\n", "")
                .replace("nbsp;", "")
                .strip()
            )

        # keywords maybe also good for generating hues
        instance.info.keywords = blob.get("KEYWORDS")

        # backup age calc
        instance.info.interest_age = blob.get("IA")
        instance.info.reading_age = blob.get("RA")

        instance.info.image_flag = blob.get("IMAGFLAG") == "Y"

        return instance

    def generate_inferred_labelset(self):
        """
        Applies business logic to particular fields to generate min/max age,
        reading ability, and recommendability. Stores result in the HydratedBookData's `labelset` object.
        """

        self.labelset = EstimatedLabelSet()

        def calculate_min_age() -> int | None:
            # CBMC code
            if self.info.cbmccode and self.info.cbmccode in CBMC_AGE_MAP.keys():
                self.labelset.age_origin = "NIELSEN_CBMC"
                return CBMC_AGE_MAP[self.info.cbmccode[0]]["min"]

            # THEMA qualifier
            for thema in self.info.thema_qualifiers:
                if thema in THEMA_AGE_MAP.keys():
                    self.labelset.age_origin = "NIELSEN_THEMA"
                    return THEMA_AGE_MAP[thema]["min"]

            # BIC qualifier
            for bic in self.info.bic_qualifiers:
                if bic in BIC_AGE_MAP.keys():
                    self.labelset.age_origin = "NIELSEN_BIC"
                    return BIC_AGE_MAP[bic]["min"]

            # interest age (IA)
            # if the string includes 'from' or does not include 'to', grab the first regex match for digits
            if self.info.interest_age and (
                "from" in self.info.interest_age.lower()
                or "to" not in self.info.interest_age.lower()
            ):
                logger.debug(
                    "Grabbing min age from interest age",
                    interest_age=self.info.interest_age,
                )
                min_age = re.search(r"/\d+/", self.info.interest_age)
                if min_age:
                    self.labelset.age_origin = "NIELSEN_IA"
                    age = int(min_age.group(0))
                    # if the string contains 'months', grab the equivalent floor age in years, otherwise return the digit as is
                    return (
                        floor(age / 12)
                        if "months" in self.info.interest_age.lower()
                        else age
                    )

            # reading age (RA)
            # if the string includes 'from' or does not include 'to', grab the first regex match for digits
            if self.info.reading_age and (
                "from" in self.info.reading_age.lower()
                or "to" not in self.info.reading_age.lower()
            ):
                min_age = re.search(r"/\d+/", self.info.reading_age)
                if min_age:
                    self.labelset.age_origin = "NIELSEN_RA"
                    age = int(min_age.group(0))
                    # if the string contains 'months', grab the equivalent floor age in years, otherwise return the digit as is
                    return (
                        floor(age / 12)
                        if "months" in self.info.reading_age.lower()
                        else age
                    )

        def calculate_max_age() -> int | None:
            # CBMC code
            if self.info.cbmccode and self.info.cbmccode in CBMC_AGE_MAP.keys():
                return CBMC_AGE_MAP[self.info.cbmccode[0]]["max"]

            # BIC qualifier
            for bic in self.info.bic_qualifiers:
                if bic in BIC_AGE_MAP.keys():
                    return BIC_AGE_MAP[bic]["max"] + 2  # add extra buffer

            # THEMA qualifier
            for thema in self.info.thema_qualifiers:
                if thema in THEMA_AGE_MAP.keys():
                    return THEMA_AGE_MAP[thema]["max"] + 2  # add extra buffer

            # interest age (IA)
            # if the string includes 'to', grab the last regex match for digits
            if self.info.interest_age and (
                "from" in self.info.interest_age.lower()
                or "to" not in self.info.interest_age.lower()
            ):
                max_age = re.findall(r"/\d+/", self.info.interest_age)
                if max_age:
                    age = int(max_age[-1])
                    # if the string contains 'months', grab the equivalent ceil age in years, otherwise return the digit as is
                    return (
                        ceil(age / 12)
                        if "months" in self.info.interest_age.lower()
                        else age + 2  # add extra buffer
                    )

            # reading age (RA)
            # if the string includes 'to', grab the last regex match for digits
            if self.info.reading_age and (
                "from" in self.info.reading_age.lower()
                or "to" not in self.info.reading_age.lower()
            ):
                max_age = re.findall(r"/\d+/", self.info.reading_age)
                if max_age:
                    age = int(max_age[-1])
                    # if the string contains 'months', grab the equivalent ceil age in years, otherwise return the digit as is
                    return (
                        ceil(age / 12)
                        if "months" in self.info.interest_age.lower()
                        else age  # add extra buffer
                    )

        def estimate_reading_abilities(
            min_age: int, max_age: int
        ) -> list[ReadingAbilityKey] | None:
            if not (min_age and max_age and self.info.pages):
                return

            def prodcc_is_young_adult() -> bool:
                return self.info.prodcc in ["Y2.2", "Y4.4"]

            def prodcc_is_childrens() -> bool:
                return self.info.prodcc and (
                    self.info.prodcc.startswith("Y1")
                    or self.info.prodcc.startswith("Y3")
                    or self.info.prodcc
                    in ["Y2.1", "Y2.3", "Y4.0", "Y4.1", "Y4.3", "Y6.0"]
                )

            def bic_is_picturebook_earlylearning() -> bool:
                bic_genres = [g for g in self.info.genres if g.source == "BIC"]
                return any(bic in ["YB"] for bic in bic_genres)

            pages = self.info.pages

            if (
                (pages >= 300 and min_age >= 10 and prodcc_is_young_adult())
                or (pages >= 500 and min_age >= 9 and max_age <= 11)
                or (pages >= 400 and min_age >= 12)
            ):
                return [ReadingAbilityKey.HARRY_POTTER]

            elif (
                (pages >= 200 and min_age >= 10 and prodcc_is_young_adult())
                or (pages >= 200 and min_age >= 12 and prodcc_is_young_adult())
                or (pages >= 400 and min_age >= 11)
                or (pages >= 200 and min_age >= 7)
            ):
                return [
                    ReadingAbilityKey.HARRY_POTTER,
                    ReadingAbilityKey.CHARLIE_CHOCOLATE,
                ]

            elif (
                (max_age < 11 and prodcc_is_young_adult())
                or (
                    pages >= 100
                    and pages <= 250
                    and min_age > 6
                    and max_age < 10
                    and not bic_is_picturebook_earlylearning()
                )
                or (pages >= 100 and pages <= 200 and min_age > 8 and max_age < 12)
                or (pages >= 300 and min_age > 4 and max_age < 8)
                or (pages >= 100 and pages <= 150 and min_age > 6 and max_age < 10)
            ):
                return [
                    ReadingAbilityKey.CHARLIE_CHOCOLATE,
                    ReadingAbilityKey.TREEHOUSE,
                ]

            if (pages <= 33 and min_age > 5 and max_age < 11) or (
                min_age > 4 and max_age < 7 and bic_is_picturebook_earlylearning()
            ):
                return [ReadingAbilityKey.SPOT]

            if pages <= 33 and min_age > 5 and max_age < 11:
                return [ReadingAbilityKey.SPOT, ReadingAbilityKey.CAT_HAT]

            if (
                min_age > 6 and max_age < 10 and bic_is_picturebook_earlylearning()
            ) or (pages >= 50 and pages <= 100 and min_age > 4 and max_age < 8):
                return [ReadingAbilityKey.CAT_HAT, ReadingAbilityKey.TREEHOUSE]

            if (
                (
                    pages >= 250
                    and pages <= 350
                    and min_age > 6
                    and max_age < 10
                    and not bic_is_picturebook_earlylearning()
                )
                or (
                    pages >= 400
                    and min_age > 6
                    and max_age < 10
                    and not bic_is_picturebook_earlylearning()
                )
                or (pages >= 200 and pages <= 350 and min_age > 8 and max_age < 12)
                or (pages >= 100 and pages <= 200 and min_age > 9 and max_age < 13)
                or (pages >= 400 and pages <= 1000 and max_age < 12)
                or (pages >= 200 and pages <= 1000 and max_age > 11)
                or (pages >= 150 and pages <= 200 and min_age > 6 and max_age < 10)
            ):
                return [ReadingAbilityKey.CHARLIE_CHOCOLATE]

            if (pages >= 33 and pages <= 50 and min_age > 4 and max_age < 8) or (
                pages >= 33 and pages <= 50 and bic_is_picturebook_earlylearning()
            ):
                return [ReadingAbilityKey.CAT_HAT]

            if (pages >= 100 and pages <= 300 and min_age > 4 and max_age < 8) or (
                pages >= 50 and pages <= 100 and not bic_is_picturebook_earlylearning()
            ):
                return [ReadingAbilityKey.TREEHOUSE]

        def estimate_recommendability() -> str | None:
            # prodcc
            if self.info.prodcc and any(
                self.info.prodcc.startswith(bad_code) for bad_code in REFERENCE_PRODCC
            ):
                return RecommendStatus.BAD_REFERENCE.name

            if self.info.prodcc and any(
                self.info.prodcc.startswith(bad_code)
                for bad_code in CONTROVERSIAL_PRODCC
            ):
                return RecommendStatus.BAD_CONTROVERSIAL.name

            # bic2sc
            bic_subject_codes = [g.code for g in self.info.genres if g.source == "BIC"]
            if any(
                any(code.startswith(bad_code) for bad_code in REFERENCE_BIC2SC)
                for code in bic_subject_codes
            ):
                return RecommendStatus.BAD_REFERENCE.name

            if any(
                any(code.startswith(bad_code) for bad_code in CONTROVERSIAL_BIC2SC)
                for code in bic_subject_codes
            ):
                return RecommendStatus.BAD_CONTROVERSIAL.name

            # themasc
            thema_subject_codes = [
                g.code for g in self.info.genres if g.source == "THEMA"
            ]
            if any(
                any(code.startswith(bad_code) for bad_code in REFERENCE_THEMA)
                for code in thema_subject_codes
            ):
                return RecommendStatus.BAD_REFERENCE.name

            if any(
                any(code.startswith(bad_code) for bad_code in CONTROVERSIAL_THEMA)
                for code in thema_subject_codes
            ):
                return RecommendStatus.BAD_CONTROVERSIAL.name

            # title
            # if any(bad_title.lower() in self.title.lower() for bad_title in BORING_TITLES):
            #     return RecommendStatus.BAD_BORING.name

            return RecommendStatus.GOOD.name

        def estimate_summary() -> str | None:
            if (
                self.info.summary_short
                and len(self.info.summary_short) > 10
                and not "synopsis coming soon" in self.info.summary_short.lower()
            ):
                return self.info.summary_short
            if (
                self.info.summary_long
                and len(self.info.summary_long) > 10
                and not "synopsis coming soon" in self.info.summary_long.lower()
            ):
                return shorten(self.info.summary_long, width=250, placeholder="...")

        min_age = calculate_min_age()
        max_age = calculate_max_age()

        if min_age and max_age is None:
            max_age = min_age + 4

        if max_age and min_age is None:
            min_age = max_age - 4

        logger.info(f"Estimated age as", min_age=min_age, max_age=max_age)
        self.labelset.min_age = min_age
        self.labelset.max_age = max_age

        reading_abilities = estimate_reading_abilities(min_age, max_age)
        if reading_abilities:
            self.labelset.reading_ability_origin = "PREDICTED_NIELSEN"
            self.labelset.reading_abilities = [ra.name for ra in reading_abilities]

        recommend_status = estimate_recommendability()
        if recommend_status:
            self.labelset.recommend_status_origin = "PREDICTED_NIELSEN"
            self.labelset.recommend_status = recommend_status

        summary = estimate_summary()
        if summary:
            self.labelset.summary_origin = "PREDICTED_NIELSEN"
            self.labelset.huey_summary = summary

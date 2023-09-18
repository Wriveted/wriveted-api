from __future__ import annotations

from typing import Annotated

import phonenumbers
from pydantic import AfterValidator


def check_phone_number(v):
    v = v.strip().replace(" ", "")
    try:
        pn = phonenumbers.parse(v)
    except phonenumbers.phonenumberutil.NumberParseException:
        raise ValueError("invalid phone number format")

    return phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.E164)


"""Phone number string, E164 format (e.g. +61 400 000 000)"""
PhoneNumber = Annotated[str, AfterValidator(check_phone_number)]

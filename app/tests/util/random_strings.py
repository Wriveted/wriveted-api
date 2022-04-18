import random
import string
from typing import Optional


def random_lower_string(length: Optional[int] = 32) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=length))

"""Reusable validated field types for request bodies."""

from typing import Annotated

from pydantic import AfterValidator, BeforeValidator, Field, StringConstraints

from booski_core.security.passwords import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH

Email = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, to_lower=True, min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+$"
    ),
]
DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
# A password being set. Length is the main strength rule (NIST SP 800-63B); no composition rules.
NewPassword = Annotated[str, Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)]
# A password being checked. Bounded so a huge body can't be used to waste hashing time.
SubmittedPassword = Annotated[str, Field(min_length=1, max_length=1024)]


def normalise_slug(value: object) -> object:
    # Lower-case before the pattern check (StringConstraints checks the pattern on the raw input).
    return value.strip().lower() if isinstance(value, str) else value


SLUG_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"
ProjectSlug = Annotated[
    str, BeforeValidator(normalise_slug), StringConstraints(min_length=2, max_length=64, pattern=SLUG_PATTERN)
]

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Name80 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Name120 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Label80 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)]
Label40 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=40)]
Text1000 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
Text2000 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
Text5000 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)]
Text10000 = Annotated[str, StringConstraints(min_length=1, max_length=10000)]
Text20000 = Annotated[str, StringConstraints(max_length=20000)]


def _https_only(value: str) -> str:
    if not value.startswith("https://"):
        raise ValueError("must be an https:// address")
    return value


HttpsUrl = Annotated[str, StringConstraints(max_length=2000), AfterValidator(_https_only)]

Tag = Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=1, max_length=40)]
Tags = Annotated[list[Tag], Field(max_length=20)]

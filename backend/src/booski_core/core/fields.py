"""Reusable validated field types for request bodies."""

from typing import Annotated

from pydantic import Field, StringConstraints

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

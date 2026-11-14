"""Password hashing with argon2id (argon2-cffi's RFC 9106 low-memory profile).

Plaintext passwords are never stored or logged. Only the encoded argon2 hash, which embeds its own
salt and parameters, is saved; ``needs_rehash`` lets parameters be strengthened later.
"""

import unicodedata
from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128  # bounds hashing work per request

PRODUCTION_HASHER = PasswordHasher()  # argon2id, time_cost=3, memory_cost=64 MiB, parallelism=4
_hasher = PRODUCTION_HASHER  # tests swap in a cheaper hasher; they assert PRODUCTION_HASHER separately


def _normalise(password: str) -> str:
    # NFKC (NIST SP 800-63B §5.1.1.2): the same passphrase typed on different keyboards or operating
    # systems produces the same bytes. Must never change once accounts exist.
    return unicodedata.normalize("NFKC", password)


def hash_password(password: str) -> str:
    return _hasher.hash(_normalise(password))


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, _normalise(password))
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    return _hasher.hash("booski-timing-equaliser-not-a-real-password")


def burn_verification_time(password: str) -> None:
    """Spends the same time as a real check, so response timing doesn't reveal whether an email exists."""
    verify_password(_dummy_hash(), password)

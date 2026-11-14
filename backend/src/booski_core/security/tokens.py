"""Random secret tokens (sessions, CSRF, invitations). Only SHA-256 hashes are ever stored.

A plain SHA-256 is appropriate here: the tokens carry 256 bits of randomness, so they cannot be
guessed or brute-forced, unlike passwords.
"""

import hashlib
import hmac
import secrets

TOKEN_BYTES = 32


def new_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> bytes:
    return hashlib.sha256(token.encode("utf-8")).digest()


def token_matches(token: str, expected_hash: bytes) -> bool:
    return hmac.compare_digest(hash_token(token), expected_hash)

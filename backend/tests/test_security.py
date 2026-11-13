"""Security primitives, independent of the database."""

from argon2 import Type

from booski_core.access.roles import MANAGEABLE_ROLES, ROLE_CAPABILITIES, Capability, Role
from booski_core.security import passwords
from booski_core.security.tokens import hash_token, new_token, token_matches


def test_production_hasher_uses_argon2id_with_strong_parameters() -> None:
    params = passwords.PRODUCTION_HASHER
    assert params.type is Type.ID
    assert params.memory_cost >= 64 * 1024  # KiB
    assert params.time_cost >= 3
    assert passwords.PRODUCTION_HASHER.hash("example password").startswith("$argon2id$")


def test_password_verification() -> None:
    encoded = passwords.hash_password("correct horse battery staple")
    assert passwords.verify_password(encoded, "correct horse battery staple")
    assert not passwords.verify_password(encoded, "wrong")
    assert not passwords.verify_password("not-a-hash", "anything")


def test_equivalent_unicode_passwords_match() -> None:
    composed = "café au lait passphrase"  # é as one code point
    decomposed = "café au lait passphrase"  # e + combining accent, as some keyboards produce
    assert passwords.verify_password(passwords.hash_password(composed), decomposed)


def test_tokens_are_long_random_and_compared_by_hash() -> None:
    first, second = new_token(), new_token()
    assert first != second
    assert len(first) >= 43  # 32 random bytes, URL-safe base64
    assert token_matches(first, hash_token(first))
    assert not token_matches(second, hash_token(first))


def test_owner_capabilities_are_a_superset_of_every_other_role() -> None:
    for role in Role:
        assert ROLE_CAPABILITIES[role] <= ROLE_CAPABILITIES[Role.OWNER]


def test_only_the_owner_can_transfer_ownership() -> None:
    holders = {role for role, caps in ROLE_CAPABILITIES.items() if Capability.OWNERSHIP_TRANSFER in caps}
    assert holders == {Role.OWNER}


def test_nobody_can_manage_the_owner_or_their_own_level() -> None:
    for role, manageable in MANAGEABLE_ROLES.items():
        assert Role.OWNER not in manageable
        if role is not Role.OWNER:
            assert role not in manageable

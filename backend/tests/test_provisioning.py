"""The operator CLI: creating the first owner, resetting passwords, and the password prompt rules."""

import io
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from booski_core import cli
from booski_core.config import get_settings
from booski_core.modules.identity.models import User
from booski_core.modules.workspaces.models import Membership, Workspace
from helpers import Account, make_user, sign_in

pytestmark = pytest.mark.db

OWNER_ARGS = [
    "create-owner",
    "--email",
    "Owner@Booski.test",
    "--name",
    "Studio Owner",
    "--workspace-name",
    "Booski Studios",
    "--workspace-slug",
    "booski",
    "--password-stdin",
]


@pytest.fixture
def cli_database(
    migrated_db: Engine, test_database_url: str, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    monkeypatch.setenv("BOOSKI_DATABASE_URL", test_database_url)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _run(args: list[str], stdin: str, monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
    return cli.main(args)


def test_create_owner_then_sign_in(
    cli_database: None,
    monkeypatch: pytest.MonkeyPatch,
    db: Session,
    client: TestClient,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert _run(OWNER_ARGS, "keep the studio lights on\n", monkeypatch) == 0
    assert "owner of workspace 'booski'" in capsys.readouterr().out

    user = db.scalars(select(User)).one()
    assert user.email == "owner@booski.test"
    workspace = db.scalars(select(Workspace)).one()
    assert db.scalar(select(Membership.role).where(Membership.workspace_id == workspace.id)) == "owner"

    owner = Account(id=user.id, email="owner@booski.test", password="keep the studio lights on")
    assert sign_in(client, owner).get("/api/v1/w/booski").json()["role"] == "owner"


def test_create_owner_rejects_weak_passwords_and_creates_nothing(
    cli_database: None, monkeypatch: pytest.MonkeyPatch, db: Session, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(OWNER_ARGS, "short\n", monkeypatch) == 1
    assert "Invalid password" in capsys.readouterr().err
    assert db.scalar(select(func.count()).select_from(User)) == 0


def test_create_owner_refuses_an_existing_account(
    cli_database: None, monkeypatch: pytest.MonkeyPatch, db: Session, capsys: pytest.CaptureFixture[str]
) -> None:
    make_user(db, "owner@booski.test")
    assert _run(OWNER_ARGS, "keep the studio lights on\n", monkeypatch) == 1
    assert "already exists" in capsys.readouterr().err
    assert db.scalar(select(func.count()).select_from(Workspace)) == 0


def test_create_owner_refuses_a_taken_workspace_address(
    cli_database: None, monkeypatch: pytest.MonkeyPatch, db: Session, capsys: pytest.CaptureFixture[str]
) -> None:
    other = make_user(db, "first@booski.test")
    db.add(Workspace(slug="booski", name="Taken", created_by_user_id=other.id))
    db.commit()
    assert _run(OWNER_ARGS, "keep the studio lights on\n", monkeypatch) == 1
    assert "already taken" in capsys.readouterr().err
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(User)) == 1  # the new owner was rolled back


def test_set_password_signs_the_user_out_everywhere(
    cli_database: None,
    monkeypatch: pytest.MonkeyPatch,
    db: Session,
    signed_in: Callable[[Account], TestClient],
) -> None:
    account = make_user(db, "ada@example.com")
    client = signed_in(account)
    assert (
        _run(
            ["set-password", "--email", "ada@example.com", "--password-stdin"],
            "a new long passphrase\n",
            monkeypatch,
        )
        == 0
    )
    assert client.get("/api/v1/auth/me").status_code == 401


def test_interactive_password_must_be_typed_twice(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = iter(["first attempt passphrase", "second attempt passphrase"])
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(answers))
    parser = cli.build_parser()
    args = parser.parse_args(["set-password", "--email", "a@example.com"])
    with pytest.raises(ValueError, match="don't match"):
        cli._read_password(args)

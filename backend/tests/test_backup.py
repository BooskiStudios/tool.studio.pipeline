"""Backups: pg_dump with a manifest, verification by restoring into a scratch database, and restore.

Needs the PostgreSQL 18 client tools (pg_dump, pg_restore). Locally they come with `booski devdb`;
CI installs them and sets BOOSKI_REQUIRE_PG_TOOLS=1 so a missing tool fails instead of skipping.
"""

import json
import os
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from psycopg import sql
from sqlalchemy import make_url
from sqlalchemy.orm import Session

from booski_core import backup, cli
from booski_core.config import Settings
from booski_core.migrations_config import migration_heads
from studio import build_studio

pytestmark = pytest.mark.db


@pytest.fixture(autouse=True)
def pg_tools() -> None:
    try:
        backup.find_tool("pg_dump")
        backup.find_tool("pg_restore")
    except backup.BackupError as error:
        if os.environ.get("BOOSKI_REQUIRE_PG_TOOLS") == "1":
            pytest.fail(str(error))
        pytest.skip(str(error))


def _admin(url: str) -> psycopg.Connection:
    return psycopg.connect(
        make_url(url).set(drivername="postgresql", database="postgres").render_as_string(hide_password=False),
        autocommit=True,
    )


def _databases(url: str) -> set[str]:
    with _admin(url) as conn:
        return {row[0] for row in conn.execute("SELECT datname FROM pg_database").fetchall()}


@pytest.fixture
def empty_target(test_database_url: str) -> Iterator[str]:
    name = (make_url(test_database_url).database or "") + "_restore_target"
    with _admin(test_database_url) as conn:
        conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    yield name
    with _admin(test_database_url) as conn:
        conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))


@pytest.fixture
def populated(db: Session) -> None:
    build_studio(db)


def test_backup_writes_a_dump_and_a_manifest_without_credentials(
    populated: None, test_database_url: str, tmp_path: Path
) -> None:
    result = backup.create_backup(test_database_url, tmp_path)
    assert result.dump.is_file() and result.dump.suffix == ".dump"
    manifest_text = result.manifest.read_text(encoding="utf-8")
    manifest = json.loads(manifest_text)
    assert manifest["format"] == "booski-backup/1"
    assert manifest["alembic_revision"] in migration_heads()
    assert manifest["tables"]["tasks"] >= 1 and manifest["tables"]["users"] >= 5
    assert manifest["size_bytes"] == result.dump.stat().st_size
    url = make_url(test_database_url)
    assert str(url.password) not in manifest_text
    assert str(url.host) not in manifest_text
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted([result.dump.name, result.manifest.name])


def test_verify_restores_into_a_scratch_database_and_drops_it(
    populated: None, test_database_url: str, tmp_path: Path
) -> None:
    result = backup.create_backup(test_database_url, tmp_path)
    verified = backup.verify_backup(result.dump, test_database_url)
    assert verified.rows == sum(result.snapshot.tables.values())
    assert verified.alembic_revision in migration_heads()
    assert not any("_restore_check_" in name for name in _databases(test_database_url))


def test_restore_into_an_empty_database_reproduces_the_data(
    populated: None, test_database_url: str, tmp_path: Path, empty_target: str
) -> None:
    result = backup.create_backup(test_database_url, tmp_path)
    restored = backup.restore_backup(result.dump, test_database_url, empty_target)
    assert restored.tables == result.snapshot.tables
    target_url = make_url(test_database_url).set(drivername="postgresql", database=empty_target)
    with psycopg.connect(target_url.render_as_string(hide_password=False)) as conn:
        emails = {row[0] for row in conn.execute("SELECT email FROM users").fetchall()}
        triggers = {
            row[0] for row in conn.execute("SELECT tgname FROM pg_trigger WHERE tgname LIKE '%append_only'")
        }
    assert {"owner@booski.test", "rival@other.test"} <= emails
    # The append-only guards on history tables come back too.
    assert triggers == {
        "activity_events_append_only",
        "document_revisions_append_only",
        "approval_reviews_append_only",
        "ai_requests_append_only",
        "agent_run_events_append_only",
    }


def test_restore_never_overwrites_a_database_with_data(
    populated: None, test_database_url: str, tmp_path: Path
) -> None:
    result = backup.create_backup(test_database_url, tmp_path)
    with pytest.raises(backup.BackupError, match="already has tables"):
        backup.restore_backup(result.dump, test_database_url)


def test_a_changed_or_damaged_dump_is_rejected(
    populated: None, test_database_url: str, tmp_path: Path
) -> None:
    result = backup.create_backup(test_database_url, tmp_path)
    with result.dump.open("ab") as handle:
        handle.write(b"tampered")
    with pytest.raises(backup.BackupError, match="checksum"):
        backup.verify_backup(result.dump, test_database_url)
    result.manifest.unlink()
    with pytest.raises(backup.BackupError, match="manifest"):
        backup.read_manifest(result.dump)


def test_failures_are_reported_and_leave_no_partial_files(
    migrated_db: object, test_database_url: str, tmp_path: Path
) -> None:
    wrong = make_url(test_database_url).set(password="definitely-wrong-password")
    with pytest.raises(backup.BackupError) as error:
        backup.create_backup(wrong.render_as_string(hide_password=False), tmp_path)
    assert "definitely-wrong-password" not in str(error.value)
    assert list(tmp_path.iterdir()) == []


def test_missing_tools_are_explained(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("BOOSKI_PG_BIN", str(tmp_path))
    monkeypatch.setattr("shutil.which", lambda _name: None)
    monkeypatch.setattr(backup, "__file__", str(tmp_path / "a" / "b" / "backup.py"))
    with pytest.raises(backup.BackupError, match="BOOSKI_PG_BIN"):
        backup.find_tool("pg_dump")


def test_cli_create_and_verify(
    populated: None,
    test_database_url: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli, "get_settings", lambda: Settings(database_url=test_database_url, backup_dir=tmp_path)
    )
    assert cli.main(["backup", "create"]) == 0
    dump = next(tmp_path.glob("*.dump"))
    assert cli.main(["backup", "verify", str(dump)]) == 0
    out = capsys.readouterr().out
    assert "Backup written" in out and "matched the manifest" in out
    assert cli.main(["backup", "verify", str(tmp_path / "missing.dump")]) == 1
    assert "does not exist" in capsys.readouterr().err

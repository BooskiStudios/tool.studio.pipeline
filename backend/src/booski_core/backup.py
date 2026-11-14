"""Database backups with PostgreSQL's own tools: ``pg_dump`` (custom format) and ``pg_restore``.

Each backup is two files:

- ``booski-<database>-<UTC time>.dump``: the ``pg_dump --format=custom`` archive.
- ``booski-<database>-<UTC time>.json``: a manifest with the dump's SHA-256 checksum, the migration
  revision and the exact row count of every table at the moment of the dump.

The row counts are taken inside the same database snapshot that ``pg_dump`` reads (an exported
snapshot), so they match the dump exactly even while the app is in use. ``verify`` restores the dump
into a throwaway database and compares the counts; ``restore`` only ever writes into an empty database.

Credentials are passed to the tools in environment variables, never on the command line (other users
could read it from the process list), and are never written into the manifest or error messages.
"""

import hashlib
import json
import os
import secrets
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql
from sqlalchemy import make_url

MANIFEST_FORMAT = "booski-backup/1"
MAINTENANCE_DATABASE = "postgres"
TOOL_TIMEOUT_SECONDS = 6 * 60 * 60


class BackupError(Exception):
    """A backup, verification or restore problem; the message says what went wrong and what to do."""


@dataclass(frozen=True)
class Snapshot:
    alembic_revision: str | None
    server_version: str
    tables: dict[str, int]


@dataclass(frozen=True)
class BackupResult:
    dump: Path
    manifest: Path
    snapshot: Snapshot


@dataclass(frozen=True)
class VerifyResult:
    tables: int
    rows: int
    alembic_revision: str | None


# ---------------------------------------------------------------- tools and connections


def find_tool(name: str) -> Path:
    """``pg_dump``/``pg_restore``: from ``BOOSKI_PG_BIN``, the ``booski devdb`` install, or ``PATH``."""
    exe = f"{name}.exe" if os.name == "nt" else name
    candidates: list[Path] = []
    if override := os.environ.get("BOOSKI_PG_BIN"):
        candidates.append(Path(override) / exe)
    candidates.append(Path(__file__).resolve().parents[2] / "var" / "postgres" / "pgsql" / "bin" / exe)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    if found := shutil.which(name):
        return Path(found)
    raise BackupError(
        f"{name} was not found. Install the PostgreSQL 18 client tools, or set BOOSKI_PG_BIN to the "
        "folder that contains them (`booski devdb setup` provides them on Windows)."
    )


def _database_name(database_url: str) -> str:
    name = make_url(database_url).database
    if not name:
        raise BackupError("The database URL doesn't name a database.")
    return name


def _conninfo(database_url: str, database: str | None = None) -> str:
    url = make_url(database_url).set(drivername="postgresql")
    if database is not None:
        url = url.set(database=database)
    return url.render_as_string(hide_password=False)


def _tool_env(database_url: str, database: str | None = None) -> dict[str, str]:
    url = make_url(database_url)
    # Start from a clean slate so stray PG* variables on the machine can't redirect the tools.
    env = {key: value for key, value in os.environ.items() if not key.startswith("PG")}
    env.update(
        {
            "PGHOST": url.host or "127.0.0.1",
            "PGPORT": str(url.port or 5432),
            "PGUSER": url.username or "",
            "PGDATABASE": database or url.database or "",
            "PGCONNECT_TIMEOUT": "10",
            "PGAPPNAME": "booski-backup",
        }
    )
    if url.password:
        env["PGPASSWORD"] = str(url.password)
    return env


def _run(command: list[str], env: dict[str, str], what: str) -> None:
    try:
        result = subprocess.run(  # noqa: S603 - fixed argument list, no shell
            command, env=env, capture_output=True, text=True, timeout=TOOL_TIMEOUT_SECONDS, check=False
        )
    except subprocess.TimeoutExpired as error:
        raise BackupError(
            f"{what} took longer than {TOOL_TIMEOUT_SECONDS // 3600} hours and was stopped."
        ) from error
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()[-2000:]
        raise BackupError(f"{what} failed (exit code {result.returncode}): {detail}")


def _connect(
    database_url: str, database: str | None = None, *, autocommit: bool = False
) -> psycopg.Connection:
    try:
        return psycopg.connect(_conninfo(database_url, database), autocommit=autocommit, connect_timeout=10)
    except psycopg.OperationalError as error:
        # psycopg's message names host/port/user but never the password.
        raise BackupError(f"Couldn't connect to the database: {str(error).strip()}") from error


def _snapshot(conn: psycopg.Connection) -> Snapshot:
    tables = [
        row[0]
        for row in conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
        ).fetchall()
    ]
    counts: dict[str, int] = {}
    for table in tables:
        row = conn.execute(
            sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier("public", table))
        ).fetchone()
        counts[table] = int(row[0]) if row else 0
    revision = None
    if "alembic_version" in counts:
        found = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        revision = str(found[0]) if found else None
    version_row = conn.execute("SHOW server_version").fetchone()
    return Snapshot(
        alembic_revision=revision, server_version=str(version_row[0]) if version_row else "", tables=counts
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _private(path: Path) -> None:
    if os.name != "nt":
        path.chmod(0o600)  # backups hold every account's data: owner-only


def manifest_path(dump: Path) -> Path:
    return dump.with_suffix(".json")


# ---------------------------------------------------------------- create


def create_backup(database_url: str, directory: Path) -> BackupResult:
    pg_dump = find_tool("pg_dump")
    database = _database_name(database_url)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    dump = directory / f"booski-{database}-{stamp}.dump"
    manifest = manifest_path(dump)
    partial = dump.with_name(dump.name + ".partial")
    if dump.exists() or manifest.exists():
        raise BackupError(f"{dump.name} already exists. Wait a second and try again.")

    try:
        with _connect(database_url) as conn:
            conn.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
            with conn.transaction():
                exported = conn.execute("SELECT pg_export_snapshot()").fetchone()
                snapshot_id = str(exported[0]) if exported else ""
                snapshot = _snapshot(conn)
                # pg_dump reads the same snapshot while this transaction stays open.
                _run(
                    [
                        str(pg_dump),
                        "--format=custom",
                        "--no-owner",
                        "--no-privileges",
                        f"--snapshot={snapshot_id}",
                        f"--file={partial}",
                    ],
                    _tool_env(database_url),
                    "pg_dump",
                )
        content = {
            "format": MANIFEST_FORMAT,
            "created_at": datetime.now(UTC).isoformat(),
            "database": database,
            "server_version": snapshot.server_version,
            "alembic_revision": snapshot.alembic_revision,
            "tables": snapshot.tables,
            "dump_file": dump.name,
            "size_bytes": partial.stat().st_size,
            "sha256": _sha256(partial),
        }
        manifest_partial = manifest.with_name(manifest.name + ".partial")
        manifest_partial.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")
        _private(partial)
        _private(manifest_partial)
        partial.replace(dump)
        manifest_partial.replace(manifest)
    except BaseException:
        for leftover in (partial, manifest.with_name(manifest.name + ".partial")):
            leftover.unlink(missing_ok=True)
        raise
    return BackupResult(dump=dump, manifest=manifest, snapshot=snapshot)


# ---------------------------------------------------------------- check, restore, verify


def read_manifest(dump: Path) -> dict[str, Any]:
    """The manifest, after checking the dump still matches its checksum."""
    if not dump.is_file():
        raise BackupError(f"{dump} does not exist.")
    path = manifest_path(dump)
    try:
        manifest: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise BackupError(f"The manifest {path.name} is missing; keep it next to the .dump file.") from error
    except json.JSONDecodeError as error:
        raise BackupError(f"The manifest {path.name} is damaged.") from error
    if manifest.get("format") != MANIFEST_FORMAT:
        raise BackupError(f"{path.name} isn't a Booski backup manifest.")
    if _sha256(dump) != manifest.get("sha256"):
        raise BackupError(f"{dump.name} doesn't match its checksum: the file is damaged or was changed.")
    return manifest


def _require_empty(database_url: str, database: str) -> None:
    with _connect(database_url, database) as conn:
        row = conn.execute("SELECT count(*) FROM pg_tables WHERE schemaname = 'public'").fetchone()
    if row and row[0]:
        raise BackupError(
            f"Database {database!r} already has tables. Restore into a new, empty database "
            "(this command never overwrites data)."
        )


def restore_backup(dump: Path, database_url: str, database: str | None = None) -> Snapshot:
    """Restore into ``database`` (default: the URL's) on the URL's server. It must exist and be empty."""
    manifest = read_manifest(dump)
    pg_restore = find_tool("pg_restore")
    target = database or _database_name(database_url)
    _require_empty(database_url, target)
    _run(
        [
            str(pg_restore),
            "--exit-on-error",
            "--single-transaction",
            "--no-owner",
            "--no-privileges",
            f"--dbname={target}",
            str(dump),
        ],
        _tool_env(database_url, target),
        "pg_restore",
    )
    with _connect(database_url, target) as conn:
        restored = _snapshot(conn)
    if restored.tables != manifest["tables"] or restored.alembic_revision != manifest["alembic_revision"]:
        raise BackupError(
            "The restored database doesn't match the backup manifest (row counts or revision differ)."
        )
    return restored


def verify_backup(dump: Path, database_url: str) -> VerifyResult:
    """Restore into a throwaway database on the same server, compare with the manifest, then drop it.

    Needs permission to create databases (true for `booski devdb` and the official PostgreSQL image).
    """
    read_manifest(dump)
    scratch = f"{_database_name(database_url)}_restore_check_{secrets.token_hex(4)}"
    with _connect(database_url, MAINTENANCE_DATABASE, autocommit=True) as admin:
        try:
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(scratch)))
        except psycopg.Error as error:
            raise BackupError(
                f"Couldn't create a scratch database to verify into: {str(error).strip()}"
            ) from error
        try:
            restored = restore_backup(dump, database_url, scratch)
        finally:
            admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(scratch)))
    return VerifyResult(
        tables=len(restored.tables),
        rows=sum(restored.tables.values()),
        alembic_revision=restored.alembic_revision,
    )

"""``booski devdb``: a private PostgreSQL 18 for local development, with no Docker and no admin rights.

Everything lives under ``backend/var/postgres`` (git-ignored). The server listens on 127.0.0.1 only,
uses password authentication, never starts on its own and is not a Windows service.
"""

import hashlib
import os
import re
import secrets
import subprocess
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

import psycopg
from psycopg import sql

PG_VERSION = "18.4"
ZIP_NAME = f"postgresql-{PG_VERSION}-1-windows-x64-binaries.zip"
ZIP_URL = f"https://get.enterprisedb.com/postgresql/{ZIP_NAME}"
# Pinned when this version was adopted. A download that doesn't match is rejected.
ZIP_SHA256 = "7effe34c0bf89027b3f171447d351cbc460f4566c8d0f643daec67f140787858"
# Only the server itself is extracted, not the bundled pgAdmin, StackBuilder or docs.
EXTRACT_PREFIXES = ("pgsql/bin/", "pgsql/lib/", "pgsql/share/")

DEFAULT_PORT = 55432
SUPERUSER = "booski"
DATABASES = ("booski", "booski_test")
ENV_DATABASE_URL = "BOOSKI_DATABASE_URL"
ENV_TEST_DATABASE_URL = "BOOSKI_TEST_DATABASE_URL"


class DevDbError(Exception):
    """A problem the user can fix; the message says how."""


@dataclass(frozen=True)
class DevDbPaths:
    root: Path  # backend/var/postgres
    env_file: Path  # backend/.env

    @property
    def downloads(self) -> Path:
        return self.root / "downloads"

    @property
    def install(self) -> Path:
        return self.root  # the zip's top-level "pgsql/" folder is created inside root

    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def log(self) -> Path:
        return self.root / "postgres.log"

    def bin_dir(self) -> Path:
        override = os.environ.get("BOOSKI_PG_BIN")
        return Path(override) if override else self.root / "pgsql" / "bin"


def default_paths() -> DevDbPaths:
    backend = Path(__file__).resolve().parents[2]
    if not (backend / "pyproject.toml").is_file():
        raise DevDbError("booski devdb only works from a source checkout (backend/pyproject.toml not found).")
    root = Path(os.environ.get("BOOSKI_DEVDB_DIR", backend / "var" / "postgres"))
    return DevDbPaths(root=root, env_file=backend / ".env")


def _exe(paths: DevDbPaths, name: str) -> Path:
    return paths.bin_dir() / (f"{name}.exe" if os.name == "nt" else name)


# ---------------------------------------------------------------- download & extract


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksum(path: Path, expected: str = ZIP_SHA256) -> None:
    actual = sha256_of(path)
    if actual != expected:
        raise DevDbError(
            f"{path.name} has SHA-256 {actual}, expected {expected}. The file is corrupt or not the "
            "pinned PostgreSQL release; delete it and run setup again."
        )


def download(url: str, destination: Path) -> None:
    if not url.startswith("https://"):
        raise DevDbError(f"Refusing to download over an insecure connection: {url}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    print(f"Downloading {url}")
    with urllib.request.urlopen(url, timeout=60) as response, partial.open("wb") as out:  # noqa: S310 (https checked above)
        total = int(response.headers.get("Content-Length", 0))
        done, next_report = 0, 10
        for chunk in iter(lambda: response.read(1024 * 1024), b""):
            out.write(chunk)
            done += len(chunk)
            if total and done * 100 // total >= next_report:
                print(f"  {next_report}%")
                next_report += 10
    partial.replace(destination)


def extract(zip_path: Path, target: Path, prefixes: tuple[str, ...] = EXTRACT_PREFIXES) -> int:
    """Extracts only members under ``prefixes``; refuses any member that would land outside ``target``."""
    target_root = target.resolve()
    count = 0
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            if not member.filename.startswith(prefixes):
                continue
            destination = (target_root / member.filename).resolve()
            if not destination.is_relative_to(target_root):
                raise DevDbError(f"Unsafe path in archive: {member.filename}")
            archive.extract(member, target_root)
            count += 1
    return count


def server_version(paths: DevDbPaths) -> str:
    result = subprocess.run(  # noqa: S603 (fixed executable path, no shell)
        [str(_exe(paths, "postgres")), "--version"], capture_output=True, text=True, check=True
    )
    match = re.search(r"(\d+)\.(\d+)", result.stdout)
    if not match:
        raise DevDbError(f"Could not read the PostgreSQL version from: {result.stdout.strip()}")
    return f"{match.group(1)}.{match.group(2)}"


def ensure_binaries(paths: DevDbPaths, zip_path: Path | None = None) -> None:
    if _exe(paths, "initdb").is_file():
        return
    if os.environ.get("BOOSKI_PG_BIN"):
        raise DevDbError(f"BOOSKI_PG_BIN is set, but {_exe(paths, 'initdb')} does not exist.")
    if os.name != "nt":
        raise DevDbError(
            "Automatic download is Windows-only. Install PostgreSQL 18 and set BOOSKI_PG_BIN "
            "to its bin folder."
        )
    if zip_path is None:
        zip_path = paths.downloads / ZIP_NAME
        if not zip_path.is_file():
            download(ZIP_URL, zip_path)
    verify_checksum(zip_path)
    print(f"Checksum OK. Extracting PostgreSQL {PG_VERSION}…")
    files = extract(zip_path, paths.install)
    print(f"Extracted {files} files to {paths.root / 'pgsql'}")


# ---------------------------------------------------------------- .env handling


def database_url(password: str, port: int, database: str) -> str:
    return f"postgresql+psycopg://{SUPERUSER}:{password}@127.0.0.1:{port}/{database}"


def update_env_file(env_file: Path, values: dict[str, str]) -> None:
    """Sets ``KEY=value`` lines, replacing existing keys and keeping every other line as it was."""
    lines = (
        env_file.read_text(encoding="utf-8").splitlines()
        if env_file.exists()
        else [
            "# Local settings for Booski Core. Git-ignored: never commit this file.",
            "BOOSKI_ENVIRONMENT=development",
        ]
    )
    remaining = dict(values)
    for index, line in enumerate(lines):
        key = line.split("=", 1)[0].strip()
        if key in remaining:
            lines[index] = f"{key}={remaining.pop(key)}"
    if remaining:
        lines.append("# Written by `booski devdb setup` (local PostgreSQL, password is local-only)")
        lines.extend(f"{key}={value}" for key, value in remaining.items())
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- server control


def _pg_ctl(paths: DevDbPaths, *args: str) -> int:
    # Output goes to DEVNULL, not a pipe: the background postgres process would otherwise inherit the
    # pipe and keep this call waiting forever on Windows. Server output goes to the log file instead.
    return subprocess.run(  # noqa: S603 (fixed executable path, no shell)
        [str(_exe(paths, "pg_ctl")), "-D", str(paths.data), *args],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode


def is_initialised(paths: DevDbPaths) -> bool:
    return (paths.data / "PG_VERSION").is_file()


def is_running(paths: DevDbPaths) -> bool:
    return is_initialised(paths) and _pg_ctl(paths, "status") == 0


def start(paths: DevDbPaths) -> None:
    if not is_initialised(paths):
        raise DevDbError("The local database isn't set up yet. Run: uv run booski devdb setup")
    if is_running(paths):
        print("Local PostgreSQL is already running.")
        return
    if _pg_ctl(paths, "-l", str(paths.log), "-w", "-t", "30", "start") != 0:
        raise DevDbError(f"PostgreSQL did not start. See the log: {paths.log}")
    print(f"Local PostgreSQL is running on 127.0.0.1:{configured_port(paths)}.")


def stop(paths: DevDbPaths) -> None:
    if not is_running(paths):
        print("Local PostgreSQL is not running.")
        return
    if _pg_ctl(paths, "-m", "fast", "-w", "stop") != 0:
        raise DevDbError(f"PostgreSQL did not stop cleanly. See the log: {paths.log}")
    print("Local PostgreSQL stopped.")


def configured_port(paths: DevDbPaths) -> int:
    conf = paths.data / "postgresql.conf"
    if conf.exists():
        ports = re.findall(r"^port\s*=\s*'?(\d+)'?", conf.read_text(encoding="utf-8"), re.MULTILINE)
        if ports:
            return int(ports[-1])  # the last setting wins
    return DEFAULT_PORT


def status(paths: DevDbPaths) -> str:
    if not _exe(paths, "postgres").is_file():
        return "not installed (run: uv run booski devdb setup)"
    if not is_initialised(paths):
        return "installed, not set up (run: uv run booski devdb setup)"
    state = "running" if is_running(paths) else "stopped (run: uv run booski devdb start)"
    address = f"127.0.0.1:{configured_port(paths)}"
    return f"PostgreSQL {server_version(paths)} on {address}: {state}. Data: {paths.data}"


# ---------------------------------------------------------------- setup


def setup(paths: DevDbPaths, port: int = DEFAULT_PORT, zip_path: Path | None = None) -> None:
    """Installs binaries, creates the cluster and databases, writes backend/.env. Safe to run again."""
    paths.root.mkdir(parents=True, exist_ok=True)
    ensure_binaries(paths, zip_path)

    version = server_version(paths)
    if not version.startswith("18."):
        raise DevDbError(f"Booski Core needs PostgreSQL 18, but these binaries are version {version}.")

    if is_initialised(paths):
        print(f"Local database already set up in {paths.data}.")
        start(paths)
        return

    password = secrets.token_urlsafe(24)
    password_file = paths.root / ".initdb-password"
    password_file.write_text(password, encoding="utf-8")
    try:
        result = subprocess.run(  # noqa: S603 (fixed executable path, no shell)
            [
                str(_exe(paths, "initdb")),
                "-D",
                str(paths.data),
                "-U",
                SUPERUSER,
                f"--pwfile={password_file}",
                "--auth=scram-sha-256",
                "--encoding=UTF8",
                "--locale=C",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        password_file.unlink(missing_ok=True)
    if result.returncode != 0:
        raise DevDbError(f"initdb failed:\n{result.stderr or result.stdout}")

    # Later lines in postgresql.conf override earlier ones. Loopback only.
    with (paths.data / "postgresql.conf").open("a", encoding="utf-8") as conf:
        conf.write(f"\n# Added by `booski devdb setup`\nlisten_addresses = '127.0.0.1'\nport = {port}\n")
    start(paths)

    admin_url = f"postgresql://{SUPERUSER}:{password}@127.0.0.1:{port}/postgres"
    with psycopg.connect(admin_url, autocommit=True) as connection:
        for name in DATABASES:
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))

    update_env_file(
        paths.env_file,
        {
            ENV_DATABASE_URL: database_url(password, port, "booski"),
            ENV_TEST_DATABASE_URL: database_url(password, port, "booski_test"),
        },
    )
    print(f"Created databases {', '.join(DATABASES)} and wrote connection settings to {paths.env_file}.")

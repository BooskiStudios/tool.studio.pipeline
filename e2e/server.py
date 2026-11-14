"""Start Booski Core for the end-to-end tests, on a freshly created, disposable database.

Run from the repository root (Playwright does this):  uv run --project backend python e2e/server.py

The database comes from BOOSKI_E2E_DATABASE_URL, or else from BOOSKI_TEST_DATABASE_URL (environment or
backend/.env) with ``_test`` swapped for ``_e2e``. Its name must end in ``_e2e``: it is dropped and
recreated on every run, so it can never be a real database. It needs a PostgreSQL user that may create
databases (true for `booski devdb` and for CI).
"""

import os
import sys
from pathlib import Path

import psycopg
from psycopg import sql
from sqlalchemy import make_url

BACKEND = Path(__file__).resolve().parents[1] / "backend"
PORT = os.environ.get("BOOSKI_E2E_API_PORT", "8765")
PASSWORD = "e2e-password-not-secret"  # noqa: S105 - test accounts in a throwaway database only
ACCOUNTS = [
    ("owner@e2e.test", "Olivia Owner", "Booski E2E Studio", "booski-e2e"),
    ("rival@e2e.test", "Rory Rival", "Rival Studio", "rival-e2e"),
]


def _env_file_value(name: str) -> str | None:
    env_file = BACKEND / ".env"
    if not env_file.is_file():
        return None
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip()
    return None


def e2e_database_url() -> str:
    url = os.environ.get("BOOSKI_E2E_DATABASE_URL")
    if not url:
        test_url = os.environ.get("BOOSKI_TEST_DATABASE_URL") or _env_file_value("BOOSKI_TEST_DATABASE_URL")
        if not test_url:
            sys.exit("Set BOOSKI_E2E_DATABASE_URL (or BOOSKI_TEST_DATABASE_URL, via `booski devdb setup`).")
        parsed = make_url(test_url)
        url = parsed.set(database=(parsed.database or "").removesuffix("_test") + "_e2e").render_as_string(
            hide_password=False
        )
    if not (make_url(url).database or "").endswith("_e2e"):
        sys.exit("The end-to-end database name must end in '_e2e' (it is wiped on every run).")
    return url


def recreate(url: str) -> None:
    parsed = make_url(url)
    admin = parsed.set(drivername="postgresql", database="postgres").render_as_string(hide_password=False)
    with psycopg.connect(admin, autocommit=True) as conn:
        name = sql.Identifier(parsed.database or "")
        conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(name))
        conn.execute(sql.SQL("CREATE DATABASE {}").format(name))


def main() -> int:
    url = e2e_database_url()
    os.environ["BOOSKI_DATABASE_URL"] = url
    os.environ["BOOSKI_ENVIRONMENT"] = "development"
    recreate(url)

    # Imported only now, so settings read the e2e database URL set above.
    from alembic import command
    from sqlalchemy.orm import Session

    from booski_core import provisioning
    from booski_core.cli import main as booski
    from booski_core.config import get_settings
    from booski_core.db import create_db_engine
    from booski_core.migrations_config import alembic_config

    command.upgrade(alembic_config(url), "head")
    engine = create_db_engine(get_settings())
    with Session(engine) as db:
        for email, name, workspace_name, workspace_slug in ACCOUNTS:
            provisioning.create_owner(
                db,
                email=email,
                display_name=name,
                password=PASSWORD,
                workspace_name=workspace_name,
                workspace_slug=workspace_slug,
            )
    engine.dispose()
    print(f"E2E database ready; Booski Core starting on 127.0.0.1:{PORT}", flush=True)
    return booski(["serve", "--port", PORT])


if __name__ == "__main__":
    raise SystemExit(main())

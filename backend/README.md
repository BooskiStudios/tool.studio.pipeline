# Booski Core

The control-plane API for the Booski Studios operating system: FastAPI, SQLAlchemy 2, Alembic and PostgreSQL 18.

**Status: PR 2.1 (foundation).** The API serves health checks only. There is no authentication yet, so it only listens on this machine (`127.0.0.1`). Workspace data arrives with PR 2.2.

## Requirements

- Python 3.13 and [uv](https://docs.astral.sh/uv/). On Windows: `winget install astral-sh.uv`.
- Nothing else on Windows: `booski devdb` downloads and runs a private PostgreSQL 18 for you.
- macOS/Linux: install PostgreSQL 18 with your package manager and set `BOOSKI_PG_BIN` to its `bin` folder (see below), or use Docker Compose.

## First-time setup (Windows)

```powershell
cd backend
uv sync                      # creates .venv with the exact versions in uv.lock
uv run booski devdb setup    # downloads PostgreSQL 18.4 (~340 MB, checksum-verified), creates the
                             # database cluster in backend/var/postgres and writes backend/.env
uv run booski devdb start
uv run booski db upgrade     # apply migrations
uv run booski serve --reload # http://127.0.0.1:8000/api/v1/health/ready
```

API docs (development only): http://127.0.0.1:8000/api/docs

## Everyday commands

| Command | What it does |
| --- | --- |
| `uv run booski devdb start` / `stop` / `status` | Start, stop or check the local PostgreSQL. It never starts on its own and is not a Windows service. |
| `uv run booski serve --reload` | Run the API on 127.0.0.1:8000 and restart on code changes. |
| `uv run booski db upgrade` | Apply all migrations. |
| `uv run booski db revision -m "add tasks"` | Generate a migration from model changes (review it before committing). |
| `uv run booski db downgrade -1` | Revert the last migration. |
| `uv run pytest` | Run the tests (database tests use the `booski_test` database). |
| `uv run ruff check . && uv run ruff format --check . && uv run mypy` | Lint, format check and type check (CI runs the same). |

## The local database

- Lives entirely in `backend/var/` (git-ignored): binaries in `var/postgres/pgsql`, data in `var/postgres/data`, log in `var/postgres/postgres.log`.
- Listens on `127.0.0.1:55432` only, with password authentication (scram-sha-256). The port is unusual on purpose, so it never clashes with another PostgreSQL.
- Has two databases: `booski` (development) and `booski_test` (wiped by the tests).
- Its password is generated during setup and stored only in `backend/.env`.
- To remove it completely: `uv run booski devdb stop`, then delete `backend/var/postgres`.
- To use your own PostgreSQL 18 binaries instead of the download, set `BOOSKI_PG_BIN` to their `bin` folder before `devdb setup`.

## Configuration

Settings are environment variables with the `BOOSKI_` prefix, read from `backend/.env` when present. See [.env.example](.env.example).

| Variable | Default | Purpose |
| --- | --- | --- |
| `BOOSKI_ENVIRONMENT` | `development` | `development`, `test` or `production`. Production hides `/api/docs`. |
| `BOOSKI_DATABASE_URL` | `postgresql+psycopg://booski@127.0.0.1:5432/booski` | Any PostgreSQL 18 server, local or managed in the cloud. |
| `BOOSKI_TEST_DATABASE_URL` | unset | Database for tests. Its name must end in `_test`, because tests wipe it. |
| `BOOSKI_LOG_LEVEL` | `INFO` | Log level. |

## Containers and cloud hosting

`Dockerfile` builds the production image, and `../docker-compose.yml` runs it with PostgreSQL for anyone who has Docker. You don't need Docker locally: CI builds the image and starts the Compose stack on every push, so the container path stays working for future cloud hosting (any container host plus a managed PostgreSQL 18 database, configured through `BOOSKI_DATABASE_URL`).

## Layout

```
src/booski_core/
  main.py              create_app() factory
  config.py            settings
  db.py                engine, sessions, Base (with constraint naming conventions)
  models.py            imports every module's models for Alembic
  health.py            /api/v1/health/live and /ready
  core/                errors (problem+json), request ids
  migrations/          Alembic environment and versions
  migrations_config.py Alembic config built in code
  devdb.py             the local PostgreSQL manager
  cli.py               the `booski` command
tests/
```

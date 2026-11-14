# Booski Core

The control-plane API for the Booski Studios operating system: FastAPI, SQLAlchemy 2, Alembic and PostgreSQL 18.

**Status: PR 2.3 (studio platform).** Accounts and roles (PR 2.2) plus the studio's persistent data: departments, projects, workstreams, milestones, tasks with comments, the knowledge base, the Decision Log, the Approvals Centre and the activity feed. The API still listens only on this machine (`127.0.0.1`): opening it to a network also needs HTTPS and a reviewed deployment, which come in a later PR. The frontend is connected in PR 2.4.

## Accounts and sign-in

There are no default accounts or passwords. Create the first owner on the server:

```powershell
uv run booski create-owner --email you@studio.com --name "Your Name" `
    --workspace-name "Booski Studios" --workspace-slug booski
# prompts twice for a password (at least 12 characters); --password-stdin reads it from a pipe instead
```

Everyone else joins by invitation: an owner or admin creates one (`POST /api/v1/w/{slug}/invitations`) and shares the one-time token. Nothing is emailed.

Operator commands: `booski set-password --email …` (signs the user out everywhere), `booski deactivate-user --email …` and `booski activate-user --email …`.

| Endpoint | Purpose |
| --- | --- |
| `POST /api/v1/auth/login` · `POST /auth/logout` | Sign in (sets cookies) · sign out this browser |
| `GET /api/v1/auth/me` | You, this session and your workspaces |
| `GET /api/v1/auth/sessions` · `DELETE /auth/sessions/{id}` · `POST /auth/sessions/revoke-others` | Your signed-in browsers |
| `POST /api/v1/auth/password` | Change password (signs out your other sessions) |
| `GET`/`POST /api/v1/workspaces` | Your workspaces · create one (you become owner) |
| `GET`/`PATCH /api/v1/w/{slug}` | Workspace details · rename |
| `GET /api/v1/w/{slug}/members` · `PATCH`/`DELETE …/members/{user_id}` | Members · change role · remove (or leave) |
| `POST /api/v1/w/{slug}/ownership` | Transfer ownership |
| `GET`/`POST /api/v1/w/{slug}/invitations` · `DELETE …/invitations/{id}` | Pending invitations · invite · revoke |
| `POST /api/v1/invitations/preview` · `POST /invitations/accept` | For the invitee (token in the body, never the URL) |

**For API clients:** after signing in, send the `csrf_token` from the login response (also in the `__Host-booski_csrf` cookie) as an `X-CSRF-Token` header on every POST, PATCH and DELETE. Errors are `application/problem+json`. Full interactive docs: `/api/docs`.

## Studio data API

Everything lives under `/api/v1/w/{workspace_slug}` and is only visible to members of that workspace. Lists return `{"items": [...], "next_cursor": …}`: pass `next_cursor` back as `?cursor=` for the next page (`?limit=` up to 200). Editable records carry a `version`; send it back in a `PATCH` and you get `409 Conflict` instead of silently overwriting someone else's change.

| Area | Endpoints |
| --- | --- |
| Departments | `GET`/`POST /departments` · `GET`/`PATCH /departments/{slug}` (rename, recolour, reorder, archive) |
| Projects | `GET`/`POST /projects` · `GET`/`PATCH /projects/{slug}` (includes progress computed from tasks, and your `capabilities` in the project) |
| Project access | `GET /projects/{slug}/members` · `PUT`/`DELETE /projects/{slug}/members/{user_id}` |
| Workstreams | `GET`/`POST /projects/{slug}/workstreams` · `PATCH …/workstreams/{id}` |
| Milestones | `GET`/`POST /projects/{slug}/milestones` · `GET`/`PATCH /milestones/{id}` |
| Tasks | `GET`/`POST /tasks` (filters: project, department, workstream, milestone, status, priority, assignee, parent, q, due_before) · `GET`/`PATCH /tasks/{id}` · `GET /tasks/{id}/history` |
| Comments | `GET`/`POST /tasks/{id}/comments` · `PATCH`/`DELETE /comments/{id}` |
| Knowledge | `GET`/`POST /documents` · `GET`/`PATCH /documents/{id}` · `GET /documents/{id}/revisions[/{n}]` |
| Decisions | `GET`/`POST /decisions` · `GET`/`PATCH /decisions/{id}` · `GET /decisions/{id}/history` |
| Approvals | `GET`/`POST /approvals` · `GET`/`PATCH /approvals/{id}` · `GET`/`POST /approvals/{id}/reviews` · `POST …/resubmit` · `POST …/cancel` |
| Activity | `GET /activity` (filters: project, entity_type, entity_id, actor, verb, since, until) |

**Who can do what** (the backend enforces all of it):

| | Owner | Admin | Developer | Collaborator | Viewer |
| --- | :-: | :-: | :-: | :-: | :-: |
| Read studio data and activity | ✓ | ✓ | ✓ | ✓ | ✓ |
| Comment on tasks | ✓ | ✓ | ✓ | ✓ | – |
| Create tasks | ✓ | ✓ | ✓ | ✓ | – |
| Edit any task | ✓ | ✓ | ✓ | own or assigned | – |
| Milestones, documents, decisions, request approvals | ✓ | ✓ | ✓ | – | – |
| Decide approvals | ✓ | ✓ | when assigned | – | – |
| Projects, workstreams, project access, departments | ✓ | ✓ | – | – | – |
| See invitation events in the activity feed | ✓ | ✓ | – | – | – |

Project rules narrow these, never widen them: a **restricted** project is invisible (404) to everyone except owners, admins and its access list, and **viewer** project access makes a project read-only for that person. Nobody can decide their own approval request.

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
| `BOOSKI_SESSION_IDLE_MINUTES` / `BOOSKI_SESSION_ABSOLUTE_DAYS` | `720` / `30` | Sign out after 12 h idle; sessions never last more than 30 days. |
| `BOOSKI_LOGIN_MAX_FAILURES_PER_EMAIL` / `…_PER_IP` / `BOOSKI_LOGIN_WINDOW_MINUTES` | `5` / `20` / `15` | Sign-in throttling. |
| `BOOSKI_INVITATION_TTL_HOURS` | `72` | How long an invitation stays valid. |
| `BOOSKI_ALLOWED_ORIGINS` | Vite and API on 127.0.0.1/localhost | JSON list of browser origins allowed to make changes. |

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

# Booski Studios — Architecture

> **What this document is:** how Booski is built, and how the planned parts will fit.
> Every section is marked with what actually exists:
>
> | Marker | Meaning |
> |---|---|
> | **Built** | Exists on `main`, tested and passing CI. |
> | **Partially built** | Some of it exists; the rest is planned. The section says which part is which. |
> | **Planned** | On the roadmap ([ROADMAP.md](ROADMAP.md)); no code exists yet. The design may still change. |
>
> Operational detail is not repeated here; it lives in the guides linked below. Decisions referenced as D*n* are in [DECISIONS.md](DECISIONS.md).

| Guide | Covers |
|---|---|
| [`README.md`](../README.md) | Running the app, frontend structure, routes, what is live versus preview. |
| [`backend/README.md`](../backend/README.md) | Booski Core setup, API summary, configuration, commands. |
| [`backend/DEPLOYMENT.md`](../backend/DEPLOYMENT.md) | Production configuration, security headers, the checklist before external access, backups and restores. |

## 1. Overview

```
                ┌──────────────────────────── BUILT ────────────────────────────┐
 Browser ──────▶│ React + TypeScript app ──/api──▶ Booski Core (FastAPI)          │
 (same origin)  │                                   Control Plane foundation      │──▶ PostgreSQL 18
                └─────────────────────────────────────────────────────────────────┘
                ┌─────────────────────────── PLANNED (Phase 3) ──────────────────┐
                │ AI Core inside Booski Core: providers & models · memory ·       │
                │ agents & orchestration · tools & permissions · usage & cost     │──▶ AI providers
                │                                                                 │    (Anthropic first)
                │ Booski Local Worker on an authorised developer machine ◀── outbound HTTPS only
                │   └─ Unity · Git · Claude Code (execution adapters)              │
                └─────────────────────────────────────────────────────────────────┘
```

**Architectural style: modular monolith (Built).** One FastAPI application and one PostgreSQL database, organised as modules with clear boundaries. Do not add microservices, message brokers, vector databases or other infrastructure without a demonstrated requirement (D-P3-2).

## 2. Technology stack (Built)

| Area | Choice | Notes |
|---|---|---|
| Frontend | React 18, TypeScript, Vite 6, React Router 7, TanStack Query 5 | Exact versions in `package-lock.json`. Existing visual design preserved since PR1. |
| Backend | Python 3.13, FastAPI, Pydantic 2 | Sync endpoints (D2). |
| Database access | SQLAlchemy 2 (sync) + psycopg 3, Alembic migrations | Exact versions in `backend/uv.lock`. |
| Database | PostgreSQL 18 | Native `uuidv7()` primary keys (D4). |
| Python tooling | uv with committed `uv.lock` (D5); ruff; mypy strict; pytest | |
| Frontend tooling | npm with committed lockfile; ESLint; Vitest; Playwright | |
| Local database | `booski devdb`: a private PostgreSQL 18 under `backend/var/` | Docker isn't used locally (D16). |
| Containers | `backend/Dockerfile` (API + built web app in one image), `docker-compose.yml` | Built and smoke-tested by CI only. |
| CI | GitHub Actions: frontend, backend, end-to-end, container jobs | See `.github/workflows/ci.yml`. |

## 3. Repository layout (Built)

```
tool.studio.pipeline/
├─ CLAUDE.md                 instructions for Claude Code sessions
├─ docs/                     vision, roadmap, architecture, status, decisions (this folder)
├─ src/                      React app (api/, auth/, workspace/, pages/, components/, config/…)
├─ e2e/                      Playwright journeys + disposable-database launcher
├─ backend/
│  ├─ src/booski_core/       FastAPI app: core/, access/, security/, modules/, migrations/, cli.py, backup.py
│  ├─ tests/                 pytest suite (real PostgreSQL)
│  ├─ Dockerfile, README.md, DEPLOYMENT.md
├─ docker-compose.yml, .github/workflows/ci.yml
```

The backend sits beside the frontend in one repository (D1).

## 4. Control Plane (Partially built)

The **Control Plane** is the planned central application that will hold accounts, workspaces, permissions, studio data, AI configuration and orchestration, and coordinate work without needing direct access to every local development environment.

**What exists today is the foundation of that Control Plane, not the complete architecture.** Booski Core, built in Phase 2, provides accounts, workspaces, permissions and studio data. It has **no** AI orchestration, agents, tool execution or worker coordination.

### Built (Phase 2): the Control Plane foundation

| Module (`backend/src/booski_core/modules/`) | What it provides |
|---|---|
| `identity` | Users (Argon2id passwords), server-side cookie sessions with CSRF tokens (D3), sign-in throttling, session management, password change. |
| `workspaces` | Workspaces, memberships with five roles, invitations (invite-only, D10), ownership transfer. |
| `departments` | Configurable departments per workspace; seven defaults are seeded (D9, D21). |
| `projects` | Projects with workspace or restricted visibility, project access lists (viewer or contributor), workstreams. |
| `milestones` | Milestones with progress computed from linked tasks. |
| `tasks` | Tasks, subtasks (up to five levels), assignment, comments, history. |
| `knowledge` | Documents (Markdown text, at most 1 MB) with immutable revisions (D7, D18). |
| `decisions` | The Decision Log: options, outcome, rationale, supporting documents, supersede flow (D6). |
| `approvals` | Approval requests, reviewer assignment, immutable review history. Approving records a decision; **it executes nothing**. |
| `activity` | Append-only activity log; also serves task and decision history (D8). |

Cross-cutting pieces that are built:

- **Workspace isolation** in two layers: application-level scoping, plus composite foreign keys that make the database reject links across workspaces. Row-level security is deferred (D13).
- **Optimistic concurrency:** editable records carry `version`; a stale write returns `409`.
- **Cursor pagination**, and errors as `application/problem+json`.
- **Append-only history:** database triggers reject updates and deletes on `activity_events`, `document_revisions` and `approval_reviews`.
- **Security headers**, serving the web app from the same origin, a production configuration check, trusted proxies. These meet explicit PR2.4 requirements; the specific design is an implementation choice (D19). See `backend/DEPLOYMENT.md`.
- **Backups:** `booski backup create | verify | restore` using `pg_dump` and `pg_restore` with checksummed manifests. The tooling was required in PR2.4; the detailed design is an implementation choice (D23).
- **CLI:** `booski serve`, `db`, `devdb`, `create-owner`, `set-password`, `activate-user`, `deactivate-user`, `backup`.

### Planned additions to the Control Plane

None of these exists:

- **AI Core:** providers, models, routing, memory, agents, tools, usage and cost (section 6; PR3.2–PR3.5).
- **Worker registry and dispatch** for the Local Worker (section 7; PR3.6).
- **AI Workforce / Command Centre APIs** (PR3.8).
- **File storage:** an open, cross-cutting requirement with no design yet (section 9).

## 5. Frontend (Built)

- **Single origin:** in development Vite proxies `/api` to Booski Core, as the PR2.4 brief required. In production the API serves the built app, an implementation choice (D19). The session cookie is `__Host-`, `HttpOnly` and `Secure`; the app never stores tokens.
- **Data layer:** `src/api/` holds a typed client (cookies, CSRF header, readable errors) and TanStack Query hooks with keys scoped by workspace. TanStack Query was an implementation choice in PR2.4, not separately approved (D20). Switching workspace clears the cache.
- **Providers:** `AuthProvider` (session from `GET /auth/me`) and `WorkspaceProvider` (active workspace, role capabilities, used only to decide which buttons to show; the server enforces everything).
- **Live versus preview:** stored records are live. AI agents, the AI command bar, usage and cost, integrations, the reference vault and some department tabs are **labelled previews** using local data in `src/data/` and `src/services/`. Department tabs and artwork are frontend configuration (`src/config/departments.ts`, D14).

## 6. AI Core (Partially built: PR3.2)

> **Two layers exist:** providers, the model catalogue and routing, the AI gateway, usage and cost tracking, and workspace AI settings (PR3.2); and memory entries, permission-aware search and context assembly (PR3.3, awaiting review). There is **no** agent, orchestration, tool execution or chat, and nothing in the web app uses AI yet: the AI screens are still labelled previews. Later layers are designed only when their milestones are approved.

**Placement (built):** inside Booski Core as a new module, `backend/src/booski_core/modules/ai/`, not a separate service (D-P3-2).

### Built in PR3.2: providers, routing and the gateway

```
caller (later: agents, workflows) ──▶ gateway.complete(task, messages, project?)
   1. permission: ai.use, narrowed by project access (D36)
   2. route: task → model + effort + max tokens (task override, else tier default) (D33)
   3. blocked if AI is off, the monthly budget is used up, or no provider is configured (D34)
   4. provider.complete(call)  ── Anthropic SDK: timeouts + retries ──▶ Anthropic API
   5. record in ai_requests (own transaction): outcome, tokens, exact cost, duration (D35)
```

| Part | Where | What it does |
|---|---|---|
| Provider interface | `modules/ai/providers/base.py` | Provider-neutral call, result and error types. Only provider adapters import a vendor SDK, so adding a provider changes no caller (D-P3-4). |
| Anthropic provider | `modules/ai/providers/anthropic.py` | Official `anthropic` SDK; key passed explicitly (D32); SDK retries for rate limits, overload, 5xx and connection errors; per-attempt timeout; errors mapped to Booski codes; refusals returned as results (D37). |
| Catalogue | `ai_models`, `ai_tiers`, `ai_tasks` (global) | Models with price bands (USD per million tokens, including cache and long-prompt rates), tier defaults and task routes. Seeded by migration 0004; changeable as data. |
| Gateway | `modules/ai/gateway.py` | The only path to a provider (steps above). |
| Request log | `ai_requests` (workspace-owned, append-only) | Metadata only; exact cost with nine decimal places. |
| Workspace settings | `workspace_ai_settings` | On/off (off by default) and monthly budget ($20 default). Changes are recorded in the activity log. |
| API | `/api/v1/w/{slug}/ai/…` | `settings`, `check`, `catalog`, `usage`, `requests`; owners and admins only (D36). |
| CLI | `booski ai check`, `booski ai seed-catalog` | Server-level key check (not tied to a workspace, not logged), and catalogue repair. |

There is deliberately **no** general chat endpoint: features built in later milestones call the gateway.

### Built in PR3.3: memory, search and context (awaiting review)

| Part | Where | What it does |
|---|---|---|
| Memory entries | `memories` (workspace-owned) · `modules/memory/` | Short facts, conventions, lessons and preferences, scoped to the workspace, a project or a department, with provenance (author, editor, optional source document or decision). Versioned, archivable, every change in the activity log. `memory.write`: developers and above (D42). |
| Search columns | `memories`, `documents` (summary), `document_revisions` (title, body), `decisions` | PostgreSQL-generated `tsvector` columns with GIN indexes (English stemming). Generated by the database, so every row is indexed however it was written (D-P3-5: no embeddings, no extra service). |
| Search | `modules/retrieval/search.py` · `GET /search` | Ranked full-text search across memory, current document revisions and decisions (D43), scoped exactly like each record's own endpoints: workspace, `project_scope` for restricted projects, archived items excluded. Every result carries its source (type, id, title, API path, version or revision). |
| Context assembly | `modules/retrieval/context.py` · `POST /ai/context` (preview) | Best matches in rank order within a token budget (conservative estimate), shortening or leaving out what doesn't fit; each block cites its source. For agents to call from PR3.4; it sends nothing to a provider. |

### Planned layers, in roadmap order

| Layer | Milestone | Intent |
|---|---|---|
| Providers and models | PR3.2 | **Built**, see above. Not yet: other providers, per-agent cost (no agents exist), per-workspace routing. |
| Memory and knowledge | PR3.3 | **Built (awaiting review)**, see above. Not yet: AI-written memories (PR3.4), tasks and milestones as sources, embeddings. |
| Agents and orchestration | PR3.4 | Agents as **configurations** (role, instructions, tools, knowledge, model, quality and escalation rules) on shared orchestration: task assignment, delegation, multi-step plans, execution history, retry and recovery, human intervention (D-P3-3). |
| Tools and execution | PR3.5 | Tool registry with schemas; permission-aware execution scoped to workspace and project; approval requirements; sandboxing, timeouts and limits; destructive-action protection. Starts with knowledge retrieval and existing platform capabilities. |
| Command Centre and AI Workforce | PR3.8 | Connects the existing interface: command bar, workforce dashboard, live progress, approvals, usage and cost, errors and human controls. |

**Toolkit input from PR3.1:** the game-development toolkit will take the form of Booski agent configurations and workflows (D27). Its contents are a [proposed specification](BOOSKI_GAME_DEV_TOOLKIT.md) (agent definition fields, an initial roster, workflows, review verdicts, guardrails), based on the [CCGS audit](audits/PR3.1-CCGS-AUDIT.md). It is an input to the PR3.2–PR3.8 designs; nothing in it is designed in detail, approved as a design, or built.

**Planned principles for every layer.** These come from the PR3.0 brief and the Phase 2 plan's text; they are to be confirmed in each milestone's design:
- AI acts with the permissions of the user who started it, and never with more.
- Future agents get no privileged path. The existing permission tests establish the user-permission behaviour that future agents must inherit: a request made with a viewer's session is refused for anything a viewer can't do (`backend/tests/test_studio_tasks.py`). No agent framework exists yet.
- Significant actions go through the existing approvals workflow (D-P3-6).
- Everything is audited in the activity log.

## 7. Booski Local Worker (Planned: not implemented)

> **Nothing in this section exists.** No worker program, worker API or worker tables are in the codebase.

The planned Local Worker is a separately installed program that would run on an **authorised developer machine** and do what needs local files and tools: the Unity editor, Git and Claude Code. This would let Booski be used remotely while development happens on the local machine. **If that machine is off, local execution is unavailable** unless an always-on execution environment is provided.

- **Agreed direction:** HTTPS long-polling with leases; WebSocket only if needed later (D15).
- **From the Phase 2 plan's worker design, not separately approved and to be confirmed in PR3.6:**
  - outbound connections only;
  - its own credentials, separate from user sessions;
  - registered to one user and one workspace.

The full design (enrolment, authentication, heartbeats, task dispatch, progress reporting, authorised directories, process execution, logs, recovery) is the subject of PR3.6. Its integration with Claude Code is PR3.7, where autonomous commits, pushes and merges must not be enabled by default.

## 8. Security model

**Built:**
- **Backend enforcement:** every endpoint authenticates the caller and checks workspace membership and role capabilities server-side. Unknown or inaccessible records return `404`, so their existence isn't revealed.
- **Roles:** Owner, Admin, Developer, Collaborator, Viewer. The capability map is in `backend/src/booski_core/access/roles.py`, mirrored for display in `src/workspace/roles.ts`. A permission matrix test covers every route.
- **Project permissions only narrow:** restricted projects are invisible to people not on their access list; viewer project access makes a project read-only.
- **Sessions:** `__Host-` HttpOnly, Secure, SameSite=Lax cookies; CSRF header on every state-changing request; a check that requests come from an allowed origin; sign-in throttling; sessions can be revoked.
- **Secrets:** environment variables and git-ignored `.env` files only, never in source control or the container build.
- **Network:** the API listens on `127.0.0.1` by default. External access requires the checklist in `backend/DEPLOYMENT.md` (HTTPS, trusted proxy, rate limiting, MFA or SSO, monitoring, backups).

**Planned:** approval gates for AI actions (destructive operations, publishing, external actions, spending, sensitive files, source control), AI spending limits, tool sandboxing, and Local Worker policy (allowed folders, tools and commands).

## 9. Open cross-cutting requirements

These are agreed needs with no milestone assigned yet. See [ROADMAP.md](ROADMAP.md#open-cross-cutting-requirements).

- **File storage:**
  - **Current system:** document content is Markdown text stored in PostgreSQL (D18).
  - **Not implemented:** any general file-storage or attachment system.
  - **Possible future approach, not designed or approved:** a local filesystem behind a storage abstraction as a starting point, with object storage as a possible later backend.
  - Needed for attachments, assets, footage and uploads. Large binaries must never be stored in PostgreSQL.
- **MFA or SSO**, **email delivery of invitations**, **scheduled backups**, **metrics export** and **multi-instance session cleanup**: listed as gaps in `backend/DEPLOYMENT.md` and tracked in ROADMAP.md.

## 10. Testing (Built)

| Suite | Where | Runs against |
|---|---|---|
| Backend unit and integration (pytest, warnings as errors) | `backend/tests/` | Real PostgreSQL. CI fails rather than skips without it, and the same applies to the PostgreSQL client tools the backup tests need. |
| Frontend unit and component (Vitest + Testing Library) | `src/**/*.test.ts(x)` | A fake API (`src/test/api.ts`). |
| End-to-end (Playwright, Chrome) | `e2e/` | The real API and a disposable `*_e2e` database. |
| Container smoke test | CI only | Built image plus Compose: readiness, served app, security headers. |

## 11. Deployment (Partially built)

**Built:** the single production image, Docker Compose, production configuration validation, health and readiness endpoints, graceful shutdown, and the backup tooling.

**Environments:**
- **Local development** uses `booski devdb` (D16).
- **Docker Compose** remains for repeatable environments and future deployment. CI builds and checks it; it isn't used on the development machine.

**Not done:** any actual hosting. Booski runs locally only. Before any external access, follow `backend/DEPLOYMENT.md`.

# Booski Studios — Studio OS v0.9

React + TypeScript + Vite frontend for the Booski Studios operating system, connected to **Booski Core** (FastAPI + PostgreSQL, in [backend/](backend/README.md)). Projects, departments, tasks, milestones, documents, decisions, approvals and activity are real, persistent and shared by everyone in a workspace. AI agents, usage reporting and integrations are clearly marked **previews** of later phases.

## Project documentation

| Document | Read it for |
|---|---|
| [CLAUDE.md](CLAUDE.md) | How to work in this repository (for Claude Code and humans alike). Start here. |
| [docs/BOOSKI_VISION.md](docs/BOOSKI_VISION.md) | What Booski is and what we are building. |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Phases 1–8 and the milestone plan (PR3.0–PR3.8). |
| [docs/CURRENT_STATUS.md](docs/CURRENT_STATUS.md) | Where the project is right now and what's next. |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | How it's built, and what's built versus planned. |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Product and architecture decisions, and open proposals. |
| [docs/BOOSKI_GAME_DEV_TOOLKIT.md](docs/BOOSKI_GAME_DEV_TOOLKIT.md) | **Proposed** (not agreed) specification of the AI workforce's game-development toolkit, from PR3.1. |
| [docs/audits/](docs/audits/) | Audits, starting with the PR3.1 audit of Claude Code Game Studios. |
| [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md) | Open-source projects whose ideas Booski builds on. |

## Run (development)

Requires Node.js 20+ and the backend set up once (see below).

```bash
# terminal 1: Booski Core on http://127.0.0.1:8000
cd backend && uv run booski devdb start && uv run booski serve --reload

# terminal 2: the app on http://localhost:5173 (Vite forwards /api to Booski Core)
npm ci
npm run dev
```

Sign in with the owner account you created with `booski create-owner` (below). Other people join by invitation: **Settings → Invite someone**, then they open `/join` and paste the code.

| Command | What it does |
| --- | --- |
| `npm run dev` | App with hot reload; `/api` is proxied to `BOOSKI_API_URL` (default `http://127.0.0.1:8000`), so the browser sees one origin. |
| `npm run build` | Type-check (`tsc -b`) and production build into `dist/`. |
| `npm run lint` | ESLint (no warnings allowed). |
| `npm test` | Unit and component tests (Vitest, fake API). |
| `npm run test:e2e` | End-to-end journeys in Chrome against the real API and a **disposable** `*_e2e` PostgreSQL database (created and wiped by `e2e/server.py`; needs `booski devdb` running and Google Chrome installed). |

`package-lock.json` is committed so every install resolves the same dependency versions. Use `npm ci` for clean installs; use `npm install <pkg>` only when deliberately adding or upgrading a dependency, and commit the updated lockfile.

## Backend (Booski Core)

The API lives in [backend/](backend/README.md) (FastAPI + PostgreSQL 18). First-time setup on Windows, with no Docker needed:

```powershell
cd backend
uv sync
uv run booski devdb setup    # private PostgreSQL 18 in backend/var, writes backend/.env
uv run booski devdb start
uv run booski db upgrade
uv run booski create-owner --email you@studio.com --name "Your Name" --workspace-name "Booski Studios" --workspace-slug booski
uv run booski serve --reload # http://127.0.0.1:8000/api/v1/health/ready
```

`docker-compose.yml` runs the API and the built app as one container, for anyone with Docker; it is the basis for future hosting. Read [backend/DEPLOYMENT.md](backend/DEPLOYMENT.md) before exposing it beyond this machine.

## Continuous integration

`.github/workflows/ci.yml` runs on every push: frontend lint, type-check, unit tests and build; backend lint (ruff), types (mypy strict) and tests (including backups) against a real PostgreSQL 18; the end-to-end journeys in Chrome against the real API and database; and a container smoke test that builds the image, starts the Compose stack and checks readiness, the served app and its security headers.

## Project structure

```
src/
  main.tsx            Entry point (query cache, router, auth provider, global CSS)
  App.tsx             Route table: /login and /join, then the signed-in studio
  routes.ts           URL builders for every page and record link
  styles.css          Global styles (unchanged visual design); app.css adds the integration UI
  api/                Booski Core client (cookies + CSRF), typed endpoints, API types, query hooks
  auth/               AuthProvider (session from /auth/me), RequireAuth
  workspace/          WorkspaceProvider (active workspace, switching), role capabilities
  config/             Department workspace presentation (tabs, actions, artwork)
  context/            Current project, task dialog, toasts
  components/         Reusable UI; tasks/, knowledge/, decisions/, approvals/, projects/ record UIs
    layout/           AppShell, Sidebar (live departments/projects, account menu), Topbar
  pages/              One component per route
  data/, services/    PREVIEW content for later phases (agents, usage, integrations…)
  test/               Unit-test helpers (fake API, providers)
e2e/                  Playwright journeys + the disposable-database server launcher
```

### Routes

| URL | Page |
| --- | --- |
| `/login`, `/join` | Sign in; accept an invitation (public) |
| `/` | Studio Command Centre |
| `/departments/:slug` | Department workspace (`concept-lab`, `game-development`, `asset-production`, `marketing-studio`, `post-launch-intelligence`) |
| `/projects/:slug` | Project workspace (`project-horizon`, `dead-frequency`, `neon-drift`) |
| `/operations` (`?view=…`) | Studio Operations |
| `/tasks` (`?task=…`) | Task Centre |
| `/library`, `/research`, `/templates` | Game Library, Research Library, Template Library |
| `/agents`, `/cost-usage`, `/decisions`, `/approvals`, `/integrations`, `/knowledge`, `/activity` | Studio Systems |
| `/settings` | Settings |

Every other page requires signing in. Departments come from Booski Core (each workspace can rename or add them); `/departments/:slug` works for all of them. Unknown URLs, departments and projects — including restricted projects you aren't on — show "Page not found". `/decisions?decision=…`, `/approvals?approval=…` and `/knowledge?document=…` open a record directly.

**Hosting note:** this is a single-page app using browser history URLs. `vite dev` and `vite preview` handle this automatically. A production host must serve `index.html` for unknown paths (an "SPA fallback"), otherwise refreshing a deep link returns a 404.

### Data flow

- **Signing in.** The session lives in an HttpOnly cookie set by Booski Core; the app never sees or stores it. On start-up `AuthProvider` asks `GET /auth/me` who is signed in. Every POST/PUT/PATCH/DELETE carries the session's CSRF token in `X-CSRF-Token` (from the sign-in response, or the readable `__Host-booski_csrf` cookie after a reload). If any request answers 401, the app drops all cached data and returns to the sign-in page with an explanation.
- **Workspaces.** `WorkspaceProvider` scopes everything to the active workspace (remembered per browser). Switching clears the cache and remounts the app, so no record from one workspace can appear in another.
- **Data.** Pages read and write through hooks in `src/api/hooks.ts` (TanStack Query): cached, refreshed in the background, cancelled when you navigate away, and re-fetched after every change so every screen agrees. Task ticks are optimistic and roll back if Booski Core refuses. Edits send the record's `version`; if someone else changed it first (409), the app says so and offers a refresh instead of overwriting their work.
- **Permissions.** Buttons appear only for what your role (and, inside a project, your project access) allows, but Booski Core enforces every rule itself.

## Live, preview and planned

| Area | Status |
| --- | --- |
| Sign-in, invitations, workspaces, members, sessions (Settings) | **Live** |
| Projects (create, edit, archive, access lists, workstreams, milestones, progress), Game Library, Studio Operations views | **Live** |
| Task Centre (filters, subtasks, comments, history), Command Centre metrics/focus/attention/activity | **Live** |
| Knowledge Base, Research Library (research documents), Template Library (template documents), revisions | **Live** (Markdown text; file uploads planned) |
| Decision Log, Approvals Centre, Activity & Audit | **Live** (approving records a decision; it executes nothing) |
| Department workspaces | **Live** tasks, documents, decisions and approvals; some tabs show labelled sample content or "planned" |
| AI command bar, AI Workforce, agent canvas, Agent Management, Cost & Usage, Integrations Hub, Reference Vault, insights/feedback/asset panels | **Preview** of later phases, labelled as such; nothing is stored or executed |

## Changelog

### v0.9 — PR 2.4: frontend integration and production readiness
- Sign-in page, invitation acceptance (`/join`), protected routes, session-expiry handling and sign-out against Booski Core; no tokens in browser storage.
- Workspace switcher in the account menu; data is scoped per workspace and dropped on switching.
- Live projects (create/edit/archive, restricted access lists, workstreams, milestones), tasks (subtasks, comments, history, optimistic completion with rollback, conflict handling), documents with revision history and safe Markdown rendering, decisions (options, outcome, supersede), approvals (request, review, resubmit, cancel) and the activity feed with filters and pagination.
- Departments come from Booski Core; department tabs combine live records with clearly labelled samples.
- Preview content is labelled everywhere it remains; demo records that are now real were removed.
- Vite proxies `/api` in development; Vitest unit tests, ESLint and Playwright end-to-end tests added.

### v0.8 — PR1: frontend foundations
- Split the single-file prototype into `pages/`, `components/`, `context/`, `hooks/`, `services/`, `data/`, `types/` and `assets/`. Replaced `any` props with typed interfaces; enabled `noUnusedLocals` / `noUnusedParameters`.
- Added React Router: every screen has its own URL; browser back/forward, refresh and deep links work.
- Added the `StudioApi` service layer so the demo data source can be replaced by Booski Core.
- Fixes: the logo is now bundled correctly (it was broken in production builds); stable React keys on all lists; agent canvas nodes are keyboard-focusable and show their tasks on focus; the canvas cursor shows "grabbing" while dragging; the agent detail panel animates out; overlapping toasts no longer cut each other short; Game Library and Template Library search work, with empty states; Decision Log shows an empty state when a department has no entries and no longer nests a full page heading inside department tabs; dialogs have `role="dialog"`, labels, Escape-to-close, focus trapping and focus return.
- Department tabs "Builds & Tests" / "Technical Docs" (Game Development) and "Reviews" / "Pipelines" (Asset Production) now show their own placeholder descriptions (they were shifted by one).
- Unknown routes show a "Page not found" page.
- Committed `package-lock.json` for reproducible installs.

### v0.7
- Sidebar navigation lives in a dedicated scrollable region; the profile control remains pinned at the bottom.
- Added Framer Motion page transitions, agent-node entrance animations and animated workflow paths.
- Agent workflow connectors use curved SVG Bezier paths with a soft glow and moving dash treatment.
- Added Recharts visualisations to Cost & Usage using explicitly labelled illustrative sample data.

### v0.5 — Studio Operations refinement
- Studio Operations focuses on Overview, Projects & Roadmaps, Tasks & Milestones, and Studio Calendar; Cost & Usage remains a dedicated Studio System.
- The agent workflow canvas can be dragged to pan; hovering or keyboard-focusing an agent reveals its demo tasks.

### v0.4 — Command Centre & studio systems
- Home became the Studio Command Centre with studio-wide metrics, illustrative AI workforce and approval items.
- Added Agent Management, Cost & Usage, a central Decision Log (with department tabs), Approvals Centre, Integrations Hub, Studio Knowledge Base and Activity & Audit.

### v0.3
- Project selection is highlighted in the sidebar only inside that project's workspace; project selector moved into the Project Overview panel.
- Game Library became a library view; Research became a document library with a file picker; Templates became a template bank.
- Reference Vault moved into project workspaces; department tabs redesigned per department.

## Next milestone
Phase 3 — AI Core & Workforce (PR3.0–PR3.8). See [docs/ROADMAP.md](docs/ROADMAP.md) for the plan and [docs/CURRENT_STATUS.md](docs/CURRENT_STATUS.md) for the current milestone.

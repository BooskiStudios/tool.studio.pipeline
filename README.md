# Booski Studios — Frontend Foundation v0.8

React + TypeScript + Vite frontend for the Booski Studios operating system. All content is **demo data**; nothing is connected to live services yet.

## Run

Requires Node.js 20+.

```bash
npm ci          # installs the exact versions in package-lock.json
npm run dev     # http://localhost:5173
npm run build   # type-check (tsc -b) + production build into dist/
npm run preview # serve dist/ locally
```

`package-lock.json` is committed so every install resolves the same dependency versions. Use `npm ci` for clean installs; use `npm install <pkg>` only when deliberately adding or upgrading a dependency, and commit the updated lockfile.

## Backend (Booski Core)

The API lives in [backend/](backend/README.md) (FastAPI + PostgreSQL 18). It is not connected to the frontend yet; that happens in PR 2.6. Quick start on Windows, with no Docker needed:

```powershell
cd backend
uv sync
uv run booski devdb setup    # private PostgreSQL 18 in backend/var, writes backend/.env
uv run booski db upgrade
uv run booski serve --reload # http://127.0.0.1:8000/api/v1/health/ready
```

`docker-compose.yml` runs the same API in containers for anyone with Docker and is the basis for future server or cloud hosting.

## Continuous integration

`.github/workflows/ci.yml` runs on every push: the frontend build; backend lint (ruff), types (mypy strict) and tests against a real PostgreSQL 18; and a container smoke test that builds the image, starts the Compose stack and waits for `/api/v1/health/ready`.

## Project structure

```
src/
  main.tsx            Entry point (BrowserRouter + global CSS)
  App.tsx             Providers and the route table
  routes.ts           URL builders for every page (use these instead of hardcoded strings)
  styles.css          Global styles (unchanged visual design)
  assets/             Logo and other bundled assets
  types/              Shared TypeScript domain types
  data/               DEMO DATA ONLY (projects, departments, agents, decisions…)
  services/           Data-access layer: StudioApi interface + demo implementation
  context/            App-wide state: projects/current project, session tasks, toasts
  hooks/              useResource (async data loading), useFocusTrap (dialogs)
  components/         Reusable UI (Modal, Icon, DecisionLogList, AgentWorkflowCanvas…)
    layout/           AppShell, Sidebar, Topbar, navigation config
  pages/              One component per route
```

### Routes

| URL | Page |
| --- | --- |
| `/` | Studio Command Centre |
| `/departments/:slug` | Department workspace (`concept-lab`, `game-development`, `asset-production`, `marketing-studio`, `post-launch-intelligence`) |
| `/projects/:slug` | Project workspace (`project-horizon`, `dead-frequency`, `neon-drift`) |
| `/operations` (`?view=…`) | Studio Operations |
| `/tasks` | Task Centre |
| `/library`, `/research`, `/templates` | Game Library, Research Library, Template Library |
| `/agents`, `/cost-usage`, `/decisions`, `/approvals`, `/integrations`, `/knowledge`, `/activity` | Studio Systems |
| `/settings` | Settings |

Unknown URLs, departments and projects show a "Page not found" page.

**Hosting note:** this is a single-page app using browser history URLs. `vite dev` and `vite preview` handle this automatically. A production host must serve `index.html` for unknown paths (an "SPA fallback"), otherwise refreshing a deep link returns a 404.

### Data flow and the future backend

Pages never import from `src/data` directly. They call the `studioApi` object exported from `src/services/index.ts`, which implements the `StudioApi` interface in `src/services/studioApi.ts`:

```ts
const decisions = useResource(() => studioApi.listDecisions(), []);
```

Today `studioApi` is `demoStudioApi`, which resolves the bundled demo data. To connect Booski Core (FastAPI), add an implementation of `StudioApi` that uses `fetch` and change the single export in `services/index.ts`. Every method is already async, and pages already handle loading and error states, so pages do not need rewriting.

`StudioApi` is read-only on purpose. No write operations exist yet. Actions such as approving, uploading, creating projects or configuring agents show a "will be connected in a later phase" notice.

## What is demo-only

- **All records and metrics** come from `src/data` and are illustrative.
- **Tasks:** adding and ticking off tasks changes browser memory only and resets on refresh.
- **Command bar:** captures and echoes your command; it is not sent to any AI model.
- **Research upload:** reads the chosen file's name only; the file is not uploaded or stored.
- **Agent canvas and charts:** visual prototypes, not live execution or real billing.

## Changelog

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
Booski Core PR 2.2: identity, workspaces, sessions and role-based permissions. A live `StudioApi` implementation follows in PR 2.6.

# CLAUDE.md — Working on Booski Studios

Booski Studios is an AI-powered operating system for an independent game studio. It is a React frontend plus **Booski Core** (FastAPI + PostgreSQL), and it is being extended with an AI workforce.

**This repository is the source of truth.** Don't rely on chat history: read the documents below, then check Git.

**The human is the decision-maker; you are the development partner.**

## 1. Before starting any task

1. Read this file.
2. Read [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md): where we are, the current approved milestone, what's next.
3. Read [`docs/ROADMAP.md`](docs/ROADMAP.md): the milestone's scope, dependencies and acceptance criteria.
4. Read [`docs/BOOSKI_VISION.md`](docs/BOOSKI_VISION.md): what we're building and why. Skim it unless the task touches product direction.
5. Read the relevant parts of [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) (what's **built** versus **planned**) and [`docs/DECISIONS.md`](docs/DECISIONS.md).
6. **Check reality:**
   - `git status`, `git branch --show-current`, `git log --oneline -5`;
   - `gh pr list --state all`, `gh run list --branch main --limit 3`.
   - If the docs disagree with the repository, the repository wins: say so, and fix the docs as part of the work.
7. Confirm the task belongs to the **current approved milestone**. If it doesn't, stop and ask.
   - A phase being "in progress" authorises only its explicitly approved milestone, not the next ones.

## 2. Answering the usual questions

| Question | Answer from |
|---|---|
| What is Booski? What are we building? | `docs/BOOSKI_VISION.md` |
| Where are we? Which phase? What's done? | `docs/CURRENT_STATUS.md`, verified with Git |
| What's the next milestone, and why that one? | `docs/CURRENT_STATUS.md` (next action) + `docs/ROADMAP.md` (dependencies) |
| Explain what we're building in this PR | `docs/ROADMAP.md` (that milestone's purpose, scope and criteria) + `docs/ARCHITECTURE.md` |
| What decisions are outstanding? | `docs/CURRENT_STATUS.md` (outstanding decisions) + the *Proposed* section of `docs/DECISIONS.md` |
| Why was X built this way? | `docs/DECISIONS.md` |
| How do I run, test or deploy it? | `README.md`, `backend/README.md`, `backend/DEPLOYMENT.md` |

When answering, separate **built**, **in progress** and **planned**.

**Never describe the future architecture as already implemented.** That covers the full Control Plane, AI Core, agents and orchestration, tool execution, the Local Worker and the Claude Code integration. What exists today (Booski Core plus the React app) is the *foundation* of the Control Plane, and contains no AI functionality.

Also keep the categories in `docs/DECISIONS.md` distinct: explicitly approved decisions, explicit requirements, implementation choices, factual records, proposals and future considerations.

## 3. Milestone status conventions

**Planned** → **In progress** (only once the human explicitly approves) → **Awaiting review** (done; human reviewing) → **Complete** (approved and merged).

- A planned item or a proposal is **never** an approved task.
- Only the human moves a milestone to *In progress* or *Complete*.
- When a milestone is planned, propose its acceptance criteria and get them agreed **before** starting.

## 4. How to work

- **Collaborate before building:** Question → Options → Decision → Draft → Approval. Challenge assumptions and explain trade-offs, but never silently make important creative, architectural or business decisions.
- **For a new milestone:**
  1. Inspect the repository.
  2. Present findings and a plan.
  3. Wait for approval.
  4. Then implement, test and stop for review.
- **Stay in scope:** don't redesign or replace working functionality. Don't add infrastructure (microservices, brokers, vector databases, new services) without a demonstrated requirement (D-P3-2). Keep the existing visual design.
- **Distinguish proposals from decisions.** Label recommendations as proposals that need approval.
- **Verify before claiming.** Never report a test, build, CI run or Git operation as successful unless you ran or checked it. Report failures with their actual output.

## 5. Git rules

- **Before creating a branch, inspect the working tree** (`git status`). Never discard, overwrite or stash away uncommitted work you didn't create.
- **One branch per milestone or PR**, created from a **verified, up-to-date `main`**: fetch, and check local `main` matches `origin/main` (fast-forward only if that's safe).
- **Branch names** follow `phase-<n>/pr<n.m>-<short-name>`, for example `phase-3/pr3.0-booski-blueprint`. Agree the exact name when the milestone is planned.
- **Never commit, push, merge, open or close PRs, delete branches, force-push or rebase shared branches without explicit approval for that action.** Approval for one action doesn't extend to the next.
- **Merging:**
  - Phase 2 was merged with PRs to `main` using **merge commits**, no squash or rebase (D22). That was agreed for **Phase 2 only**; it is not a standing rule.
  - For each future merge, propose a strategy and get the human's approval.
  - Wait for CI to pass after each merge.
- **Commit messages:** existing history uses a concise imperative subject naming the milestone, for example "Add complete studio backend platform (PR 2.3)". Follow that pattern unless the human asks otherwise.
- **Report** the actual branch, commit SHA and CI result after any Git operation.

## 6. Actions that always need human approval

Destructive operations; publishing; significant external actions; spending money; sensitive file operations; source-control actions (commit, push, merge); anything outside the approved milestone.

The same rule applies to features you build: AI agents must not get autonomous commit, push or merge by default (D-P3-6).

## 7. Keeping the documentation current

**Update the docs in the same branch as the work:**
- **`docs/CURRENT_STATUS.md`:** whenever the real state changes (milestone status, merges, branches, CI, blockers, next action).
- **`docs/ROADMAP.md`:** only when an **agreed** milestone or roadmap decision changes, including the milestone's status line.
- **`docs/DECISIONS.md`:** for every significant **approved** decision, as a new entry. Never rewrite history: supersede old entries. Mark unknowns as "needs historical confirmation". Record proposals under *Proposed*.
- **`docs/ARCHITECTURE.md`:** when something moves from planned to built, or the design changes.
- **`CLAUDE.md`:** when the working process changes.

**Mark a milestone Complete only after the human approves and it is merged.** Something appearing on the roadmap is never evidence that it was built.

## 8. Engineering guardrails (built system)

- **Security is enforced server-side.**
  - Every endpoint authenticates the caller and checks workspace membership and role capabilities (`backend/src/booski_core/access/`).
  - Project access may **narrow** workspace permissions, never widen them.
  - Inaccessible records return `404`.
  - The frontend's role map (`src/workspace/roles.ts`) only decides which buttons to show.
- **Workspace isolation:** every workspace-owned table has `workspace_id` and composite foreign keys. Keep both when adding tables. The permission-matrix test fails if a new route isn't covered.
- **Schema changes:** new Alembic migrations only, reversible, preserving existing data. Never edit an existing migration.
- **History stays append-only:** `activity_events`, `document_revisions` and `approval_reviews`. Record significant actions in the activity log.
- **Secrets never go in source control.** `.env` files are git-ignored. Never print tokens or passwords.
- **No large binaries in PostgreSQL.** File storage is an open requirement (D-P3-11).
- **Preview versus live:** UI for unbuilt capabilities must stay clearly labelled as a preview. Never present fake persistence as real.
- **Tests come with every change.** Backend tests use real PostgreSQL. CI must not skip database or backup tests.

## 9. Commands

```bash
# Backend (from backend/)
uv sync
uv run booski devdb start            # local PostgreSQL 18 on 127.0.0.1:55432 (no Docker; D16). `stop` when done.
uv run booski db upgrade
uv run booski serve --reload         # API on http://127.0.0.1:8000
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv lock --check
uv run pytest -W error               # needs the dev database running

# Frontend (repository root)
npm ci
npm run dev                          # http://localhost:5173, proxies /api to :8000
npm run lint && npm run build && npm test
npm run test:e2e                     # Playwright + real API on a throwaway booski_e2e database (ports 8765/5174)
```

## 10. Environment notes

- **Development machine:** Windows 11. Docker Desktop is **not** used; containers are verified by CI only. Use `booski devdb` for PostgreSQL.
- **Installing dependencies:** prefer versions published at least two weeks ago (`npm install --before=<date>`; uv uses `exclude-newer` in `backend/pyproject.toml`).
- **End-to-end tests:** they create and wipe a `booski_e2e` database. Drop it afterwards to keep the dev cluster tidy.
- **Stray processes:** on Windows, stopped `vite` processes can leave node or esbuild children that lock `node_modules`. Find and stop only those processes.
- **GitHub:** the `gh` CLI is authenticated for the repository `BooskiStudios/tool.studio.pipeline`.

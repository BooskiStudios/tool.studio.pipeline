# Booski Studios — Decisions

> **What this document is:** the record of important product and architecture decisions, and of significant implementation choices and outcomes, each classified by how it came about.
>
> **Rules for this file**
> - Never rewrite a past decision. If it changes, add a new entry that **supersedes** it and update the old entry's status line only.
> - Only record what is known. Where a date, reason or alternative can't be verified from the available records, it says **"needs historical confirmation"** or **"not recorded"**.
> - Never upgrade a classification (for example from *implementation choice* to *explicitly approved decision*) without evidence of the human's explicit approval.
> - A proposal or future consideration is never treated as agreed.
> - Add an entry whenever a milestone makes or changes something significant, in the same branch as the work.

## Classifications

| Category | Meaning |
|---|---|
| **Explicitly approved decision** | The human explicitly approved this specific decision. |
| **Explicit requirement** | The human stated it as a requirement or constraint in a brief. |
| **Implementation choice** | Chosen by Claude while implementing an approved milestone. Accepted only through the human's approval of that milestone as a whole, not discussed or approved separately. |
| **Factual implementation record** | Something that happened or exists. It records the outcome, not a decision. |
| **Unknown historical origin** | Exists or happened, but who decided it and why isn't recorded. |
| **Proposal** | Recommended and awaiting the human's decision. Not agreed. |
| **Future consideration** | A note about something that may need revisiting later. Not part of any original decision; not agreed. |

**Sources for the Phase 2 entries:**
- **The Phase 2 architecture plan** ("Booski Core: backend architecture and PR2 plan", based on commit `ee8206f`). Its section 11 listed D1–D15, each with a recommendation and a main alternative, plus risks and assumptions. It was written as a Claude artifact and isn't stored in this repository, so this file is the repository's copy of those decisions.
- **The human's approval of all fifteen recommendations** ("Happy with all of those!"). The date, 13 November 2026, comes from Claude's session notes; the message itself carries no timestamp in the available record.
- **The human's briefs and approval messages** for PR2.3, PR2.4 and the Phase 2 merges, plus the merged code on `main`.

## Index

| ID | Subject | Category | Status |
|---|---|---|---|
| D1–D15 | Phase 2 architecture | Explicitly approved decisions | See each entry |
| A1 | Docker Desktop available locally (plan assumption) | Recorded assumption | Invalidated by D16 |
| D16 | Local development without Docker (`booski devdb`) | Explicitly approved decision | Implemented |
| D17 | PR2 delivered as PR2.1–PR2.4 | Factual implementation record | Completed |
| D18 | No large binaries in PostgreSQL; documents as Markdown text | Explicit requirement + implementation choice | Implemented |
| D19 | Single origin; API serves the built app; security headers | Explicit requirement + implementation choice | Implemented |
| D20 | TanStack Query as the frontend data layer | Implementation choice | Implemented |
| D21 | Seven default departments | Factual implementation record · unknown historical origin | Implemented |
| D22 | Phase 2 merged as stacked PRs with merge commits | Explicitly approved decision (Phase 2 only) | Completed |
| D23 | Backups with PostgreSQL's own tools | Explicit requirement + implementation choice | Implemented |
| D24 | PR3.0 merged with a merge commit; status updated by follow-up PR | Explicitly approved decision (PR3.0 only) | Completed |
| D25 | Branch protection on `main` (PROP-1 accepted) | Explicitly approved decision | Implemented |
| D26 | PR3.1 approved, with its scope decisions | Explicitly approved decision | In effect |
| D27 | Toolkit target: Booski agent configurations (Route A) | Explicitly approved decision (accepts PROP-3) | Agreed; not built |
| D28 | Acknowledge CCGS when CCGS-inspired features are built | Explicitly approved decision (resolves PROP-4) | Agreed; not yet due |
| D29 | Unity 6.3 LTS is the studio's Unity version; upgrades expected | Explicitly approved decision | Agreed |
| D-P3-1 … D-P3-13 | Phase 3 direction | Agreed direction (see note on IDs) | Agreed |
| PROP-1 | Protect `main` | Proposal | Accepted; implemented as D25 |
| PROP-2 | Delete the five merged Phase 2 branches | Proposal | Awaiting decision |
| PROP-3 | Toolkit target: Booski agent configurations (Route A), repository pack derived | Proposal (from PR3.1) | Accepted as D27 |
| PROP-4 | Acknowledge CCGS as an inspiration | Proposal (from PR3.1) | Decided as D28 |

---

## Phase 2 architecture decisions (D1–D15)

**Category:** explicitly approved decisions. The human accepted all fifteen recommendations in the plan, on 13 November 2026 according to Claude's session notes.

**How to read these entries:**
- The **Decision** and **Main alternative** lines reproduce the plan's decision table.
- **Reasoning** is given only where the plan's own text states it; otherwise it says "not recorded".
- **Outcome** records what was implemented, and is a factual implementation record.
- **Future consideration** lines are later notes and were not part of the original decision.

### D1 — Repository layout
- **Decision:** Add `backend/` beside the frontend in this repo; leave the frontend at the root for now.
- **Main alternative:** Restructure into `frontend/` + `backend/` now (more churn).
- **Reasoning:** not recorded beyond the "(more churn)" note on the alternative.
- **Outcome:** the frontend stays at the repository root. The Docker image is built from the root (`docker build -f backend/Dockerfile .`).

### D2 — Database access style
- **Decision:** Sync SQLAlchemy 2.0 + psycopg 3, plain `def` endpoints.
- **Main alternative:** Async SQLAlchemy throughout.
- **Reasoning (stated in the plan):** sync endpoints are easier to debug and test, and FastAPI runs them in a thread pool. The concurrency given up doesn't matter at studio scale. If the worker long-poll endpoint needs async later, that one endpoint can be async.
- **Outcome:** all current endpoints are sync.
- **Future consideration (not part of the original decision):** when the Local Worker is designed (PR3.6), check whether its long-poll endpoint should be the one async exception the plan anticipated.

### D3 — Browser auth mechanism
- **Decision:** Server-side sessions in HttpOnly cookies + CSRF header.
- **Main alternative:** JWT access and refresh tokens (harder to revoke).
- **Reasoning:** no separate reasoning was recorded. The only rationale in the plan is the comparison in its decision table: the alternative, JWTs, are "harder to revoke".
- **Outcome:** `__Host-` cookies and an `X-CSRF-Token` header; the frontend never handles tokens.

### D4 — Database version and IDs
- **Decision:** PostgreSQL 18 with native `uuidv7()`.
- **Main alternative:** PostgreSQL 16/17 with UUIDv7 generated in Python.
- **Reasoning (stated in the plan):** UUIDv7 IDs are time-ordered, so indexes stay compact, and they're safe to expose in URLs.
- **Outcome:** every primary key defaults to `uuidv7()` (`backend/src/booski_core/db.py`). PostgreSQL 18 is the minimum version.

### D5 — Python toolchain
- **Decision:** Python 3.13, managed with uv, committed `uv.lock`.
- **Main alternative:** Poetry, or pip-tools.
- **Reasoning:** not recorded; needs historical confirmation.
- **Outcome:** `uv sync --locked` in CI and in the image.

### D6 — Decision Log
- **Decision:** Add it as its own small module (not in the brief, but used on 3 screens).
- **Main alternative:** Store decisions as a knowledge document kind.
- **Reasoning (stated in the plan):** the Decision Log was missing from the brief's module list but is used on three screens.
- **Outcome:** the `decisions` module was built in PR2.3, with options, outcome, rationale, supporting documents and a supersede flow.

### D7 — Knowledge model
- **Decision:** One `knowledge_documents` table with a `kind` covering research, templates, guides and references.
- **Main alternative:** A separate table for each.
- **Reasoning:** not recorded; needs historical confirmation.
- **Outcome:** implemented as `documents` + `document_revisions`. Kinds: guide, research, template, reference, design_doc, note, report. The Research and Template libraries are filtered views. For how content is stored, see D18.

### D8 — Task history
- **Decision:** Use the single append-only `activity_events` table.
- **Main alternative:** A dedicated `task_history` table.
- **Reasoning (stated in the plan):** one table serves both the audit log and task history.
- **Outcome:** task and decision history endpoints read `activity_events`. The plan proposed enforcing append-only through database role grants; it was implemented with database triggers that reject `UPDATE` and `DELETE`. The same trigger mechanism also protects `document_revisions` and `approval_reviews`.

### D9 — Departments
- **Decision:** Seed the current 5 per workspace; allow renaming later.
- **Main alternative:** Fixed global departments.
- **Reasoning:** not recorded; needs historical confirmation.
- **Outcome:** departments are per-workspace and configurable, but **seven** defaults are seeded, not five. How that came about is unknown (see D21).

### D10 — Sign-up
- **Decision:** Invite-only; first owner created through the CLI.
- **Main alternative:** Open self-registration.
- **Reasoning:** not recorded; needs historical confirmation.
- **Outcome:** `booski create-owner`, one-time invitation codes and the `/join` page. No public sign-up exists.

### D11 — Screens without modules
- **Decision:** Assets, player feedback, milestones, insights and usage stay demo-labelled in PR2.
- **Main alternative:** Add minimal modules for them now.
- **Reasoning:**
  - **Usage (stated in the plan):** real usage numbers only exist once agents run.
  - **Assets, player feedback, milestones and insights:** not recorded.
- **Outcome:**
  - Milestones were built in PR2.3, as part of that milestone's brief.
  - Assets, feedback, insights and usage remain labelled previews.

### D12 — Status and kind columns
- **Decision:** `text` + `CHECK` constraints.
- **Main alternative:** PostgreSQL `ENUM` types.
- **Reasoning (stated in the plan):** adding a status is then a simple migration.
- **Outcome:** allowed values live in `backend/src/booski_core/vocab.py` and feed both constraints and API schemas.

### D13 — Row-level security
- **Decision:** Defer; enforce scoping in the app and test it thoroughly.
- **Main alternative:** Enable PostgreSQL RLS from the start.
- **Reasoning (stated in the plan):** scoping happens in the application and is checked by a permission-matrix test suite.
- **Outcome:** in effect. Composite foreign keys also reject links across workspaces at database level.
- **Future consideration (not part of the original decision):** revisit if multiple studios or external hosting raise the risk.

### D14 — UI configuration
- **Decision:** Department tabs, actions and descriptions, and agent canvas positions, become frontend config.
- **Main alternative:** Store them in the database.
- **Reasoning (stated in the plan):** they are layout and copy, so they belong in frontend configuration rather than the database.
- **Outcome:** `src/config/departments.ts` (PR2.4). The agent canvas remains a labelled preview using local data.

### D15 — Worker transport
- **Decision:** HTTPS long-polling with leases; WebSocket later if needed.
- **Main alternative:** WebSocket from day one.
- **Reasoning:** the plan's worker design leases runs from PostgreSQL (`FOR UPDATE SKIP LOCKED`) and needs no queue broker. No further reasoning was recorded.
- **Outcome:** not built. It is the agreed starting direction for PR3.6, whose own design must confirm it.

### A1 — Recorded assumption: Docker Desktop is available
- **Category:** recorded assumption. It was stated in the plan's "Assumptions" list, not presented as a decision.
- **Assumption (as written in the plan):** "Docker Desktop with WSL 2 is available on the Windows development machine." The plan's local-development design (`docker compose up` for PostgreSQL and the API) depended on it.
- **Status:** **invalidated** on 13 November 2026. Docker Desktop couldn't be used on the development machine (see D16).
- **Other assumptions in the same plan list (summarised, not verbatim):**
  - a team of up to about 20 people and a few workspaces;
  - one region, English only;
  - GBP as the default display currency;
  - Unity as the first engine target;
  - frontend and API always served from the same origin;
  - no regulated personal data beyond names and email addresses.

  These are recorded here for completeness; none was separately approved.

---

## Later Phase 2 entries (D16–D23)

These entries cover what happened after the plan was approved. Each is classified honestly: several are implementation choices or factual records, not separately approved decisions.

### D16 — Local development without Docker
- **Category:** explicitly approved decision.
- **Date:** 13 November 2026 (from Claude's session notes).
- **Evidence:**
  - The human: "I don't think we can use docker desktop. What are the other options?"
  - Then, choosing the first option offered: "I like option 1, as long as we can host this in the cloud later when we expand beyond local."
  - The other options offered were not preserved: needs historical confirmation.
- **Decision:** local development uses `booski devdb`, which downloads (checksum-verified) and runs a private PostgreSQL 18 under `backend/var/`, on `127.0.0.1:55432`. Docker Desktop isn't used on the development machine.
- **Outcome:** `docker-compose.yml` and `backend/Dockerfile` remain for repeatable environments and future hosting, and CI's container job builds and checks them. This invalidates assumption A1.

### D17 — PR2 delivered as four PRs
- **Category:** factual implementation record. No separate approval of the re-scoping was found.
- **What happened:**
  - The plan described PR2.1–PR2.6.
  - The human's subsequent briefs defined PR2.3 as "Complete Backend Platform" and PR2.4 as "Frontend Integration & Production Readiness".
  - Phase 2 was therefore delivered as four PRs: 2.1 foundation, 2.2 identity and access, 2.3 complete backend platform, 2.4 frontend integration and production readiness.
  - Claude's session notes date the re-scope to 13 November 2026.
- **Reasoning:** not recorded; needs historical confirmation.
- **Outcome:**
  - The plan's PR2.5 items were not built: the agent registry, integrations, dashboard and usage endpoints, and worker tables. ROADMAP.md lists a **proposed** mapping of these items to Phase 3 milestones; that mapping has not been agreed.
  - The plan's `seed-demo` command was **not built**. There is no record that it was deliberately dropped.

### D18 — Document content storage
- **Category:** explicit requirement + implementation choices.
- **Explicit requirement (PR2.3 brief):** "Do not store large binary files directly in PostgreSQL."
- **Implementation choices (PR2.3, accepted through approval of PR2.3 as a whole; not separately discussed or approved):**
  - Document content stored as Markdown text in PostgreSQL;
  - a 1 MB limit per document;
  - immutable revisions.
- **Date:** PR2.3 was committed on 14 November 2026. The exact date of the choices needs historical confirmation.
- **Outcome:** the plan's `stored_objects` table and storage layer weren't built. No general file-storage or attachment system exists (see D-P3-11).

### D19 — Single origin and production hardening
- **Category:** explicit requirement + implementation choices.
- **Explicit requirements (PR2.4 brief):**
  - a Vite development proxy so that "the browser should treat API calls as same-origin";
  - security headers (nosniff, frame protection, cache control, minimal server-identifying headers);
  - documenting proxy-aware client IP handling and HTTPS expectations.
- **Implementation choices (PR2.4, accepted through approval of PR2.4 as a whole; not separately approved):**
  - In production, the API serves the built web app, so one container image holds both.
  - The specific Content Security Policy, plus HSTS in production.
  - Production refuses non-HTTPS origins.
  - Forwarded headers are trusted only from the proxies listed in `BOOSKI_TRUSTED_PROXIES`.
- **Date:** 14 November 2026 (PR2.4).
- **Outcome:** external access still requires the `backend/DEPLOYMENT.md` checklist.

### D20 — Frontend data layer
- **Category:** implementation choice. Not separately discussed or approved.
- **Choice (PR2.4):** TanStack Query for caching, background refresh, cancellation and invalidation, with cache keys scoped by workspace. Switching workspace drops all cached data.
- **Claude's reasoning at the time:** shared, consistent state across screens without building a cache by hand. This was not reviewed separately.
- **Date:** 14 November 2026 (PR2.4).
- **Outcome:** one added runtime dependency. The old demo `StudioApi` survives only as the source of preview content.

### D21 — Seven default departments
- **Category:** factual implementation record · unknown historical origin.
- **What exists:**
  - Seven departments are seeded into every workspace: Concept Lab, Game Development, Asset Production, Marketing Studio, Studio Operations, Quality & Oversight and Post-Launch Intelligence.
  - Existing workspaces received them through migration `0003` (PR2.3, committed 14 November 2026).
- **Unknown:** who chose seven instead of D9's "current 5", and why. Needs historical confirmation.
- **Note:** the same seven names appear as departments in the PR3.0 brief (see BOOSKI_VISION.md). That is consistent with the implementation but isn't evidence of the original choice.

### D22 — How Phase 2 was merged
- **Category:** explicitly approved decision, **for Phase 2 only**.
- **Date:** 14 November 2026.
- **Evidence:** the human chose "Option A" (stacked PRs) and then said "Lets do it, merge them".
- **Decision:** PRs #1–#5 were merged in order with **merge commits**: no squash, no rebase, no force-push. CI had to pass on `main` after each merge.
- **Alternatives presented:** a single combined Phase 2 PR with a merge commit; fast-forwarding `main` without PRs.
- **Reasoning presented:** this keeps the original commits and their CI runs, and a review record per phase.
- **Scope:** agreed for the Phase 2 merges only. It is **not** a standing rule for future milestones: each future merge strategy needs the human's approval.

### D23 — Backups
- **Category:** explicit requirement + implementation choices.
- **Explicit requirement (PR2.4 brief):** a backup and restore process using PostgreSQL's established tooling, with a restoration verification test, safe credential handling, no backup files in Git, and testing only against a disposable database.
- **Implementation choices (PR2.4, accepted through approval of PR2.4 as a whole; not separately approved):**
  - the `booski backup create | verify | restore` commands;
  - a manifest with a SHA-256 checksum and exact row counts from the same snapshot as the dump;
  - restore only into an empty database;
  - credentials passed through environment variables.
- **Date:** 14 November 2026 (PR2.4).
- **Outcome:** scheduled backups and retention automation remain open.

---

## Phase 3 entries

### D24 — How PR3.0 was merged
- **Category:** explicitly approved decision, **for PR3.0 only**.
- **Date:** 14 November 2026.
- **Evidence:** the human gave final approval to commit and merge PR3.0, then chose "Merge commit" for the merge strategy and "Follow-up PR" for the status update.
- **Decision:**
  - PR #6 was merged into `main` with a **merge commit** (`65755f1`), after its CI passed.
  - Marking PR3.0 Complete was done afterwards in a separate docs-only PR, so the status records the real merge commit and CI run.
- **Alternatives presented:** squash merge or rebase merge; for the status update, a direct commit to `main` or leaving it for a later session.
- **Scope:** agreed for PR3.0 (and its follow-up status PR) only. Like D22, it is **not** a standing rule: each future merge strategy needs the human's approval.

### D25 — Branch protection on `main`
- **Category:** explicitly approved decision. Accepts PROP-1.
- **Date:** 14 November 2026.
- **Evidence:** after PR3.0 merged, Claude recommended doing PROP-1 first and then planning PR3.1; the human replied "Lets do it".
- **Decision (as applied through the GitHub API):**
  - The four CI jobs must pass before anything merges into `main`: "Frontend lint, types, tests and build", "Backend lint, types and tests", "End-to-end (browser + API + PostgreSQL)" and "Container smoke test".
  - Force-pushes to `main` and deleting `main` are blocked.
  - The rules apply to administrators too, so no one (including Claude through `gh`) can push unchecked commits directly to `main`. Changes reach `main` through pull requests.
- **Implementation choices (not separately discussed):**
  - Branches are **not** required to be up to date with `main` before merging.
  - No pull-request review is required, because the human is the only reviewer.
- **Consequence:** documentation updates to `main`, including status updates, also go through pull requests.
- **Reversal:** the human can change these settings in GitHub (Settings → Branches) at any time; record any change here.

### D26 — PR3.1 approved, with its scope decisions
- **Category:** explicitly approved decision.
- **Date:** 14 November 2026.
- **Evidence:** Claude proposed the PR3.1 plan, acceptance criteria and branch name, with three questions. The human answered:
  - "don't choose yet: make sure the audit looks at both and recommends one, and I'll decide then";
  - "You suggestion is good";
  - "put it on the PR3.1 branch as its first commit".
- **Decision:**
  - PR3.1 (Open-Source Capability Adoption Audit) proceeds on `phase-3/pr3.1-ccgs-audit`, documentation only, with the acceptance criteria recorded in ROADMAP.md.
  - **Toolkit route:** the audit assesses both routes (Booski agent configurations; a curated `.claude/` toolkit for game repositories) and recommends one. **The human makes the choice afterwards** (see PROP-3).
  - **Engines:** Unity specialists are reviewed in depth; Godot and Unreal are marked "not now" without detailed review; the browser-prototype route is assessed only for concepts worth borrowing.
  - **Branch protection:** recorded as D25 in the first commit on the PR3.1 branch.
- **Scope note:** approving PR3.1 doesn't approve any of the audit's recommendations, or any later milestone.

### D27 — Toolkit target: Booski agent configurations (Route A)
- **Category:** explicitly approved decision. Accepts PROP-3.
- **Date:** 14 November 2026.
- **Evidence:** after reviewing the PR3.1 audit, the human said "Route A sounds better".
- **Decision:** the game-development toolkit takes the form of **Booski agent configurations and workflows**, run by Booski's orchestrator with server-side permissions, approvals and audit. Booski will generate a small `.claude/` guidance pack for each game repository from its own definitions (PR3.7), rather than installing CCGS's toolkit.
- **Alternative not chosen:** Route B, a curated copy of CCGS's `.claude/` toolkit installed into game repositories.
- **What it does not decide:** the toolkit's contents ([BOOSKI_GAME_DEV_TOOLKIT.md](BOOSKI_GAME_DEV_TOOLKIT.md)) remain a proposal; each part is confirmed when its milestone (PR3.2–PR3.8, Phases 4–7) is planned.

### D28 — When to acknowledge CCGS
- **Category:** explicitly approved decision. Resolves PROP-4.
- **Date:** 14 November 2026.
- **Evidence:** asked whether to add the acknowledgement now or with the first CCGS-inspired build, the human answered "When the features are built".
- **Decision:** add an acknowledgements note crediting Claude Code Game Studios (MIT, Copyright (c) 2026 Donchitos) in the **same milestone that first builds a CCGS-inspired feature**. Any substantial reused text is recorded then in `THIRD_PARTY_NOTICES.md` with the full MIT text, source path and pinned commit.
- **How to apply:** when planning PR3.2 or any later milestone, check whether it builds anything from the PR3.1 audit; if so, include the acknowledgement in that milestone's scope.

### D29 — Unity version
- **Category:** explicitly approved decision.
- **Date:** 14 November 2026.
- **Evidence:** the human: "Unity 6.3LTS but just be aware we'll want to be looking to update at some point."
- **Decision:** the studio uses **Unity 6.3 LTS**. An upgrade is expected later.
- **Consequences for design (to confirm when Phase 4 and PR3.7 are planned):**
  - Treat the Unity version as a **per-project setting**, not a studio-wide constant, so a project can be upgraded deliberately and independently.
  - Any Unity reference material or agent guidance is scoped to the version a project uses; an upgrade is a tracked change with its own review.
  - Agents check the project's pinned version before using an engine API, and mark anything unverified.

---

## Phase 3 direction (D-P3-1 – D-P3-13)

**Source:** the PR3.0 brief and the human's approval of the PR3.0 plan, both 14 November 2026.

> **About these IDs:** D-P3-1 to D-P3-13 are **organisational references created for this documentation**. They group the direction stated in the PR3.0 brief and the approval message. They are **not** evidence that each item was approved separately as an independent decision. The agreed source is the brief as a whole.

| ID | Agreed direction | Where it comes from |
|---|---|---|
| D-P3-1 | **The repository is the permanent source of truth.** `CLAUDE.md` at the root plus five documents in `docs/`; future sessions must not rely on chat history. | PR3.0 brief; layout confirmed in the approval message |
| D-P3-2 | **Modular monolith.** No microservices, message brokers, vector databases or extra infrastructure without a demonstrated requirement. | PR3.0 brief §4 |
| D-P3-3 | **Agents are configurations on shared orchestration**, not independent AI systems. Four autonomy levels. The human is the final decision-maker. Design flow: Question → Options → Decision → Draft → Approval. | PR3.0 brief §5 |
| D-P3-4 | **Anthropic is the first AI provider; the architecture is provider-agnostic**, so others (for example OpenAI) can be added without rebuilding the core. | PR3.0 brief §3.1 |
| D-P3-5 | **Memory starts with structured PostgreSQL and full-text search**; embeddings or vector search only when justified. | PR3.0 brief, PR3.3 |
| D-P3-6 | **Approval is required** for destructive operations, publishing, significant external actions, spending money, sensitive file operations and source-control actions. **Autonomous commit, push and merge are off by default.** Significant actions are auditable. | PR3.0 brief §4.3, PR3.7 |
| D-P3-7 | **Unity and C# first**; Unreal Engine later. | PR3.0 brief §3.3 |
| D-P3-8 | **Post-launch sources:** Steam first, then Discord and YouTube. | PR3.0 brief §3.8 |
| D-P3-9 | **The roadmap:** Phase 3 = PR3.0–PR3.8 as numbered; Phases 4–8 are strategic direction, not commitments. | PR3.0 brief §7–8 |
| D-P3-10 | **The CCGS audit is its own milestone (PR3.1).** No wholesale import of `donchitos/claude-code-game-studios`; reuse only after review, preserving MIT licence and copyright notices. | PR3.0 brief §7, §12 |
| D-P3-11 | **File storage is an open, cross-cutting future requirement.** It is not attached to PR3.3 or PR3.6. The brief's stack names a local filesystem behind a storage abstraction as the initial approach; how and when to build it is undecided. | PR3.0 brief §4; approval message |
| D-P3-12 | **Phase 1** = the original frontend prototype (v0.3–v0.7), whose recorded history ends at `d3acf5f` on 4 November 2026. **Phase 2** = PR1 + PR2.1–PR2.4. | Approval message ("subject to commit verification"); see the caveat below |
| D-P3-13 | **AI cost principles:** prefer deterministic tools, cheaper models for routine work, context reuse and caching; track cost by workspace, project, agent, provider and task. | PR3.0 brief §6 |

**Phase 1 verification caveat (D-P3-12):** checked on 14 November 2026.
- The prototype entered the repository as one commit, `87c1b04` "Created Frontend". Individual prototype versions aren't represented in the history.
- `README.md` at `d3acf5f` still said "v0.3", but the code there already contains the v0.4–v0.7 features. The v0.4–v0.7 changelog was written up later, in PR1.

**Development environments (D16 + PR3.0 brief):**
- **Local development** uses `booski devdb` (D16).
- **Docker Compose** remains available for repeatable environments and future deployment: the brief's stack lists it, and CI builds and checks it.

These are complementary, not in conflict.

---

## Future considerations (not agreed)

Notes for later review. None of these is a decision.

- **D2:** whether the Local Worker's long-poll endpoint should be async (PR3.6 design).
- **D13:** whether to enable row-level security if multiple studios or external hosting raise the risk.
- **D29:** when to upgrade beyond Unity 6.3 LTS, and how Booski supports a project's upgrade (a planned workflow, version-scoped guidance, re-running tests).

## Proposals — awaiting a decision

These are recommendations only. **Do not act on them without explicit approval.**

### PROP-1 — Protect `main`
- **Status:** **accepted** on 14 November 2026 and implemented; see D25. The proposal text below is kept as written.
- **Category:** proposal.
- **Proposal:** enable branch protection on `main`: require the four CI jobs (frontend, backend, end-to-end, container) to pass, and disallow force-pushes and branch deletion.
- **Why:** `main` was unprotected when checked on 14 November 2026.

### PROP-2 — Delete merged Phase 2 branches
- **Category:** proposal.
- **Proposal:** delete the five merged branches `phase-2/pr1-frontend-foundations`, `phase-2/pr2.1-backend-foundation`, `phase-2/pr2.2-identity-access`, `phase-2/pr2.3-complete-backend-platform` and `phase-2/pr2.4-frontend-integration`, on GitHub and locally.
- **Why:** all were fully merged into `main` through PRs #1–#5. Their commits remain in `main`'s history.
- **Note:** the PR3.0 planning discussion referred to "six" merged branches. That was a miscount: there were five `phase-2/*` branches when checked on 14 November 2026. Re-check with `git branch -a --merged origin/main` before deleting.

### PROP-3 — Toolkit target: Booski agent configurations
- **Status:** **accepted** on 14 November 2026; see D27. The proposal text below is kept as written.
- **Category:** proposal, from the PR3.1 audit ([audit §7](audits/PR3.1-CCGS-AUDIT.md#7-the-two-routes-assessment-and-recommendation)).
- **Proposal:** the game-development toolkit takes the form of Booski agent configurations and workflows (Route A), run by Booski's orchestrator with server-side permissions and approvals. In PR3.7, Booski generates a small `.claude/` guidance pack for each game repository from its own definitions, rather than installing CCGS's toolkit.
- **Alternative:** Route B, a curated copy of CCGS's `.claude/` toolkit installed into game repositories.
- **Why:** consistent with D-P3-3, D-P3-4 and D-P3-6, covers every department, and avoids tracking a fast-moving fork. Route B is quicker to try but keeps logic and approvals outside Booski, and can't start before PR3.6–PR3.7.
- **Decided by:** the human (D26).

### PROP-4 — Acknowledge CCGS as an inspiration
- **Status:** **decided** on 14 November 2026: acknowledge when the features are built; see D28. The proposal text below is kept as written.
- **Category:** proposal, from the PR3.1 audit ([audit §8](audits/PR3.1-CCGS-AUDIT.md#8-licence-obligations)).
- **Proposal:** add an acknowledgements note crediting Claude Code Game Studios (MIT, Copyright (c) 2026 Donchitos) as an inspiration for Booski's workforce design. Any substantial reused text goes into a `THIRD_PARTY_NOTICES.md` with the full MIT text, source path and pinned commit.
- **Open point:** add the note now, or with the first CCGS-inspired build.

## Open questions (no decision yet)

Tracked in [CURRENT_STATUS.md](CURRENT_STATUS.md#outstanding-decisions) and [ROADMAP.md](ROADMAP.md#open-cross-cutting-requirements). Record answers here when they are made.

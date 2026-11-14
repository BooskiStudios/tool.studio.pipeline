# Booski Studios — Roadmap

> **What this document is:** the agreed plan, Phases 1–8, with the milestone numbering, scope, dependencies and acceptance criteria.
> The live state of each milestone (branches, commits, CI, what's next) is in [CURRENT_STATUS.md](CURRENT_STATUS.md). The vision behind it is in [BOOSKI_VISION.md](BOOSKI_VISION.md).
>
> Update this file only when an **agreed** milestone or roadmap decision changes, and record why in [DECISIONS.md](DECISIONS.md).

## Status conventions

| Status | Meaning |
|---|---|
| **Planned** | On the roadmap, not yet started. Scope may still change. |
| **In progress** | Explicitly approved by the human and started. |
| **Awaiting review** | Work is done and waiting for human review and approval. |
| **Complete** | Reviewed, approved and merged into `main`. |

A planned or proposed item is **never** an approved task. Only the human moves a milestone to *In progress* or *Complete*.

## At a glance

| Phase | Theme | Status |
|---|---|---|
| 1 | Frontend prototype | **Complete** |
| 2 | Platform foundations (PR1, PR2.1–PR2.4) | **Complete** |
| 3 | AI Core & Workforce (PR3.0–PR3.8) | **In progress**: PR3.0 is complete. PR3.1 is approved and awaiting review. PR3.2–PR3.8 are planned and not authorised. |
| 4 | Game Development Intelligence | Planned (strategic) |
| 5 | Concept Lab & Asset Production | Planned (strategic) |
| 6 | Marketing Studio & Studio Operations | Planned (strategic) |
| 7 | Post-Launch Intelligence | Planned (strategic) |
| 8 | Cross-Project Studio Intelligence | Planned (strategic) |

---

## Phase 1 — Frontend prototype · Complete

A single-file React + TypeScript + Vite prototype of the whole studio interface, using demo data. It covered the Command Centre, the five department workspaces, project workspaces, the Studio Systems pages (agents, cost and usage with charts, decisions, approvals, integrations, knowledge, activity) and the agent workflow canvas.

- **Versions:** v0.3–v0.7. The changelog is in `README.md`.
- **Repository history:** the prototype was uploaded as one commit, `87c1b04` "Created Frontend" (4 November 2026), followed by housekeeping. Phase 1 ends at **`d3acf5f`** "Update .gitignore" (4 November 2026). Earlier versions predate the repository, so they aren't separate commits.
- **Note:** `README.md` at `d3acf5f` still said "v0.3", but the code there already contains the v0.4–v0.7 features (verified 14 November 2026). The v0.4–v0.7 changelog was written up in PR1.

## Phase 2 — Platform foundations · Complete

Turned the prototype into a real, persistent, multi-user platform: the Control Plane foundation. All five PRs were merged into `main` on 14 November 2026 as stacked PRs with merge commits (D22).

| Milestone | Scope | Commits | GitHub PR → merge commit | CI evidence |
|---|---|---|---|---|
| **PR1** Frontend foundations | Routed, typed React app; `StudioApi` service layer; accessibility fixes | `ee8206f` | #1 → `2b2f963` | No CI (the workflow arrived in PR2.1) |
| **PR2.1** Backend foundation | FastAPI, PostgreSQL 18, Alembic, `booski` CLI, `booski devdb`, Docker, CI | `00c5024`, `cdef01f` | #2 → `c0a6658` | Branch run 43510406731 ✅; `main` run 43585379687 ✅ |
| **PR2.2** Identity & access | Accounts, sessions + CSRF, workspaces, roles, invitations, activity log | `bbe98dc` | #3 → `e956594` | Branch run 43514888876 ✅; `main` run 43585478829 ✅ |
| **PR2.3** Complete backend platform | Departments, projects (restricted access, workstreams), milestones, tasks, documents and revisions, decisions, approvals, activity API; migration `0003` | `b11d272` | #4 → `de24448` | Branch run 43576028274 ✅; `main` run 43585653650 ✅ |
| **PR2.4** Frontend integration & production readiness | Sign-in, workspaces, live screens, security headers, single-origin serving, backups, Vitest + Playwright | `dc6b4c0`, `5e6abb7` | #5 → `a68d829` | Branch run 43584364106 ✅ (the earlier run 43583348129 failed the container job; fixed by `5e6abb7`); `main` run 43585888671 ✅ |

The original Phase 2 plan described PR2.1–PR2.6, but Phase 2 was delivered as the four PRs above. This is recorded as a historical implementation outcome (D17); no separate approval of the re-scoping is recorded. The plan's unbuilt items (agent registry, integrations, dashboard and usage endpoints, worker tables) are **proposed** to be covered by Phase 3 milestones, as noted below. That mapping isn't agreed yet.

---

## Phase 3 — AI Core & Workforce · In progress

**Goal:** build the shared AI infrastructure: providers, memory, agents, tools, the Local Worker and Claude Code execution. Bring it into the existing interface.

> **Phase 3 being "in progress" authorises only the milestones the human has explicitly approved:** PR3.0 (complete) and PR3.1 (approved 14 November 2026). It does **not** authorise work on PR3.2 or any later milestone. Each milestone starts only when the human explicitly approves it, after its plan and acceptance criteria are agreed.

**Dependencies:** each milestone builds on the ones before it. The diagram shows the proposed dependency order, implied by the agreed numbering. Confirm a milestone's exact dependencies when it is planned.

```
PR3.0 ─▶ PR3.1 (audit; informs PR3.4/3.5 design)
   └───▶ PR3.2 ─▶ PR3.3 ─▶ PR3.4 ─▶ PR3.5 ─▶ PR3.6 ─▶ PR3.7
                                     └──────────────────────▶ PR3.8 (needs 3.4 and 3.5; 3.7 for execution views)
```

> **Acceptance criteria for PR3.2–PR3.8 are *proposed*.** (PR3.1's were agreed when it was approved.) They are derived from each milestone's agreed capability list. Confirm and refine them with the human when the milestone is planned, before it moves to *In progress*.

### PR3.0 — Booski Blueprint & Project Documentation · Complete
- **Purpose:** make the repository the permanent source of truth, so a fresh Claude Code session understands the product, the plan and the state.
- **Scope:** `CLAUDE.md`; `docs/BOOSKI_VISION.md`, `ROADMAP.md`, `ARCHITECTURE.md`, `CURRENT_STATUS.md`, `DECISIONS.md`; README links. **Documentation only.**
- **Out of scope:** any application, schema or behaviour change; the CCGS audit (PR3.1); housekeeping (PROP-1, PROP-2).
- **Dependencies:** Phase 2 complete.
- **Acceptance criteria (agreed):**
  1. Repository inspected; current status verified.
  2. Vision, architecture, Phase 1–8 roadmap and PR3.0–PR3.8 numbering documented consistently.
  3. Decisions recorded accurately, with unknowns marked.
  4. `CLAUDE.md` holds the permanent working instructions.
  5. No duplicated or conflicting sources of truth.
  6. No application behaviour changed; Git changes cleanly scoped.
- **Branch:** `phase-3/pr3.0-booski-blueprint`.
- **Delivered:** commit `abafcd6`; merged on 14 November 2026 through PR #6 with a merge commit, `65755f1` (D24). CI: PR runs 43626305259 and 43626320236 ✅; `main` run 43626588068 ✅. Status marked Complete in a follow-up docs-only PR (`phase-3/pr3.0-status-complete`).

### PR3.1 — Open-Source Capability Adoption Audit · Awaiting review
- **Purpose:** decide what Booski should **reuse, adapt, rebuild or ignore** from [`donchitos/claude-code-game-studios`](https://github.com/donchitos/claude-code-game-studios) (MIT).
- **Scope:** review its specialist agents, agent hierarchy, skills and workflows, hooks, rules, templates, production stages, approval gates and documentation conventions. Produce a proposed **Booski Game Development Toolkit** specification. **Documentation only.**
- **Approved scope decisions (D26):**
  - Assess both toolkit routes (Booski agent configurations; a curated `.claude/` toolkit for game repositories) and recommend one; the human decides.
  - Review the Unity specialists in depth; mark Godot and Unreal "not now" without detailed review; assess the browser-prototype route only for concepts worth borrowing.
  - Record PROP-1 as D25 in the first commit on this branch.
- **Constraints:** no wholesale import; reuse only after review; preserve the MIT licence and copyright notices on anything reused (D-P3-10).
- **Dependencies:** PR3.0.
- **Acceptance criteria (agreed):**
  1. The source is pinned to a commit, and its licence is recorded.
  2. Every capability area is classified as reuse, adapt, rebuild or ignore, with a reason for each.
  3. Agents, hooks, rules and gates are classified individually. Skills are grouped by workflow family, with a per-skill appendix.
  4. The toolkit specification maps onto the planned Booski architecture and is clearly labelled a proposal.
  5. Licence obligations are listed.
  6. No third-party files are imported, and no application, schema or CI changes are made.
  7. All documentation stays consistent: links check out, and nothing planned is described as built.
- **Deliverables:** [audits/PR3.1-CCGS-AUDIT.md](audits/PR3.1-CCGS-AUDIT.md) (pinned to CCGS commit `abc0de7`) and [BOOSKI_GAME_DEV_TOOLKIT.md](BOOSKI_GAME_DEV_TOOLKIT.md) (proposed specification).
- **Branch:** `phase-3/pr3.1-ccgs-audit`.

### PR3.2 — AI Core Foundation · Planned
- **Scope:**
  - Provider registry and model registry.
  - Anthropic integration on an extensible provider architecture (D-P3-4).
  - Model routing.
  - Central request handling with timeouts and retries.
  - Usage and cost tracking.
  - AI request logs.
  - Workspace configuration.
- **Proposed to absorb (not yet agreed):** the Phase 2 plan's usage endpoint (real usage figures).
- **Dependencies:** PR3.0.
- **Proposed acceptance criteria:**
  - A second provider could be added without changing callers.
  - Requests are scoped and permission-checked by workspace.
  - Provider secrets are never returned by the API or committed.
  - Every request records tokens and cost.
  - Timeouts and retries are tested.
  - Tests mock providers; no live API calls in CI.

### PR3.3 — Persistent AI Memory & Knowledge · Planned
- **Scope:**
  - Workspace, project and department memory.
  - Decisions and lessons.
  - Integration with the knowledge base.
  - Context assembly.
  - **Permission-aware retrieval.**
  - Provenance and source tracking.
- **Approach:** structured PostgreSQL and full-text search first; embeddings only when justified (D-P3-5).
- **Dependencies:** PR3.2.
- **Proposed acceptance criteria:**
  - Retrieval never returns content the requesting user can't see, including restricted projects; covered by tests.
  - Every retrieved item carries its source.
  - Context size stays within budget.

### PR3.4 — Agent Framework & Orchestration · Planned
- **Scope:**
  - Agent definitions (role, responsibilities, configuration).
  - Task assignment and delegation.
  - Multi-step plans with shared context.
  - Execution history and progress tracking.
  - Retry and recovery; human intervention.
- **Proposed to absorb (not yet agreed):** the Phase 2 plan's agent registry.
- **Dependencies:** PR3.2, PR3.3. Informed by PR3.1.
- **Proposed acceptance criteria:**
  - Agents are configurations (D-P3-3) and act with no more than the starting user's permissions.
  - Runs are recorded and auditable.
  - A human can pause, stop or redirect a run.

### PR3.5 — Tools, Permissions & Execution · Planned
- **Scope:**
  - Tool registry with schemas.
  - Permission-aware execution within workspace and project scope.
  - Approval requirements (D-P3-6).
  - Execution logs.
  - Sandboxing, timeouts and limits.
  - Destructive-action protection.
- **Initial tools:** approved knowledge retrieval and existing Booski platform capabilities.
- **Dependencies:** PR3.4.
- **Proposed acceptance criteria:**
  - Every tool call is authorised server-side and logged.
  - Tools that need approval cannot run before it is granted.
  - Limits are enforced and tested.

### PR3.6 — Booski Local Worker · Planned
- **Scope:**
  - Secure registration and authentication.
  - Heartbeats.
  - Task dispatch and progress reporting.
  - Authorised project directories and filesystem permissions.
  - Process execution and execution logs.
  - Recovery and reconnection.
- **Starting direction:** outbound-only HTTPS long-polling with leases (D15); credentials separate from user sessions.
- **Proposed to absorb (not yet agreed):** the Phase 2 plan's worker enrolment tables and endpoints.
- **Dependencies:** PR3.5.
- **Proposed acceptance criteria:**
  - A worker can't act outside its authorised directories, or for another user or workspace.
  - Lost workers' runs are recovered.
  - Credentials can be revoked instantly.
  - A separate security review is held before merge.

### PR3.7 — Claude Code Integration · Planned
- **Scope:**
  - An execution adapter for Claude Code through the Local Worker.
  - Session and task management; repository access.
  - Task-specific instructions and project context.
  - Branch creation and Git workflow support.
  - Progress, output and test results; diff inspection.
  - Human review and approval.
- **Constraint:** **autonomous commits, pushes and merges are not enabled by default** (D-P3-6).
- **Dependencies:** PR3.6.
- **Proposed acceptance criteria:**
  - Every repository-changing action requires approval.
  - Diffs and test results are shown before approval.
  - Everything is logged in the activity history.

### PR3.8 — Command Centre & AI Workforce · Planned
- **Scope:** connect the **existing** interface, without redesigning it:
  - A functional AI command bar.
  - An AI workforce dashboard with agent status.
  - Task assignment and delegation.
  - Live progress and an activity timeline.
  - Approval workflows.
  - Model usage and costs.
  - Execution history, error reporting and human controls.
- **Proposed to absorb (not yet agreed):** the Phase 2 plan's dashboard aggregates. The preview panels would then become live.
- **Dependencies:** PR3.4, PR3.5; PR3.7 for execution views.
- **Proposed acceptance criteria:**
  - No preview label remains on a feature that's now live, and none is removed from a feature that isn't.
  - The existing visual design is preserved.
  - Human controls work end to end.

---

## Phases 4–8 — Strategic roadmap · Planned

These are direction, not commitments. Each phase is broken into numbered milestones only when it is planned.

| Phase | Theme | Intended capabilities |
|---|---|---|
| 4 | Game Development Intelligence | Unity integration; project inspection; understanding scripts, scenes and prefabs; development assistance; debugging; automated testing; build and verification workflows; game-development specialist agents. |
| 5 | Concept Lab & Asset Production | Ideation; research; design documentation; mechanics and systems design; worldbuilding; feasibility and scope analysis; prototyping; asset creation and management. |
| 6 | Marketing Studio & Studio Operations | Devlog production; trailer workflows; social content; promotional assets; content planning; release management; studio reporting. |
| 7 | Post-Launch Intelligence | Steam, then Discord and YouTube feedback; sentiment and feedback classification; bug and feature prioritisation; approved issue-to-task workflows; patch impact monitoring. |
| 8 | Cross-Project Studio Intelligence | Shared studio knowledge; cross-project learning; reusable systems; development insights; better future concepts. |

---

## Open cross-cutting requirements

Agreed needs with **no milestone assigned yet**. Assign one only with the human's approval.

| Requirement | Notes |
|---|---|
| **File storage** (D-P3-11) | No general file-storage or attachment system exists; documents are Markdown text in PostgreSQL (D18). A local filesystem behind a storage abstraction is a possible starting point, with object storage a possible later backend. Neither is built or designed. Needed for attachments, assets, footage and uploads; large binaries never go in PostgreSQL. Not attached to PR3.3 or PR3.6. |
| **MFA or SSO** | Required before external access (`backend/DEPLOYMENT.md`). |
| **Email delivery of invitations** | Invitation codes are currently shared by hand. |
| **Scheduled backups and retention** | The backup tooling exists (D23); scheduling and off-site copies don't. |
| **Metrics export** | Operational metrics for monitoring. Listed as a gap in `backend/DEPLOYMENT.md`; only health and readiness endpoints exist. |
| **Multi-instance session cleanup** | Listed as a gap in `backend/DEPLOYMENT.md`; relevant only if more than one API instance runs. |
| **Integrations module** | The Phase 2 plan's integrations catalogue (secrets, per-agent grants) wasn't built. Where it belongs (PR3.5, or Phases 4, 6 or 7) is undecided. |

**Development environments:** local development uses `booski devdb` (D16). Docker Compose remains available for repeatable environments and future deployment; CI builds and checks it. No hosting environment exists yet.

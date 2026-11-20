# Booski Studios — Current Status

> **What this document is:** the actual state of the project as last verified. Update it whenever the real state changes (a merge, a new branch, CI results, a decision) in the same branch as the change.
>
> **Last verified:** 20 November 2026, while building PR3.5 on branch `phase-3/pr3.5-tools-execution` (after PR #15 was merged).
>
> The Git, PR and CI facts below are **results of that verification, not guarantees about the present**. Every new session must re-check them before relying on them:
> - `git status`, `git branch -a`, `git log origin/main -5`;
> - `gh pr list --state all`, `gh run list --branch main --limit 5`.
>
> If the live facts disagree with this file, the repository wins: say so, and correct this file.

## Where we are

- **Phase:** Phase 3 — AI Core & Workforce is in progress.
- **Current approved milestone:** **PR3.5 — Tools, Permissions & Execution**, approved 20 November 2026 (D54).
  - **Status: Awaiting review.** Built and tested locally on `phase-3/pr3.5-tools-execution`; at last verification it was not pushed and no PR was open.
  - What it adds: agents use tools inside their steps (eight read tools; three propose tools for documents, tasks and decisions). Proposed changes are applied only when a person approves the run's review, all or nothing. Every tool call is permission-checked as the starter, limited and logged. Backend only.
- **Last completed milestone:** **PR3.4 — Agent Framework & Orchestration**. Merged into `main` through PR #14 (merge commit `93a860a`); CI on `main` passed.
  - What it added: per-workspace agents (Producer, Technical Director, Game Designer, QA Lead), agent runs executed by `booski agent-worker` (plan, delegated steps, final deliverable, review approval), human control and crash recovery. Developers may now use AI (D50). Backend only; no tools.
- **Before that:** **PR3.3 — Persistent AI Memory & Knowledge** (PR #12, `39ae4ab`): memory entries, permission-aware search, context assembly. **PR3.2 — AI Core Foundation** (PR #10, `1bad661`): the AI gateway, the Anthropic provider, task-based routing with prices, usage and cost tracking, workspace AI settings. No live call to Anthropic has been made yet: the server has no key configured (`booski ai check` proves a key once one is added, D32).
- **Next milestone:** **PR3.6 — Booski Local Worker**. **Status: Planned.** Not approved, not started.
- **What exists today:** a working, persistent, multi-user studio application (Booski Core plus the React interface). It is the **foundation for the future Booski Control Plane**, not the completed Control Plane architecture described in [ARCHITECTURE.md](ARCHITECTURE.md). It stores accounts, workspaces, roles, departments, projects, milestones, tasks, documents, decisions, approvals and activity. The repository also holds the project documentation (`CLAUDE.md` and `docs/`), which is the source of truth for the plan and process.
- **AI:** the AI Core foundation (providers, routing, gateway, usage and cost, workspace settings; PR3.2) and memory, search and context assembly (PR3.3) are built and merged. They are backend-only: no web-app feature uses them yet.
- **What does not exist:**
  - AI-related screens (command bar, AI workforce, agents, cost and usage, integrations) are still **labelled previews**.
  - No memory system, agent, orchestration, tool execution, Local Worker, Claude Code integration or file storage has been built.

## Completed milestones

| Milestone | PR commit(s) | Merge into `main` | CI evidence |
|---|---|---|---|
| **Phase 1** — Frontend prototype (v0.3–v0.7) | Initial history (see note below) | — (`main` started from this history) | None existed |
| **PR1** — Frontend foundations | `ee8206f` | PR #1, merge commit `2b2f963` (14 Nov 2026) | None existed (the CI workflow arrived in PR2.1) |
| **PR2.1** — Backend foundation | `00c5024`, `cdef01f` | PR #2, merge commit `c0a6658` | `main` run 43585379687 ✅ |
| **PR2.2** — Identity & access | `bbe98dc` | PR #3, merge commit `e956594` | `main` run 43585478829 ✅ |
| **PR2.3** — Complete backend platform | `b11d272` | PR #4, merge commit `de24448` | `main` run 43585653650 ✅ |
| **PR2.4** — Frontend integration & production readiness | `dc6b4c0`, `5e6abb7` | PR #5, merge commit `a68d829` | `main` run 43585888671 ✅ (all four jobs) |
| **PR3.0** — Booski Blueprint & Project Documentation | `abafcd6` | PR #6, merge commit `65755f1` (14 Nov 2026; merge commit approved for this PR, D24) | PR runs 43626305259 and 43626320236 ✅; `main` run 43626588068 ✅ (all four jobs) |
| **PR3.1** — Open-Source Capability Adoption Audit | `cca88f2`, `995cfe3`, `0c100bf` | PR #8, merge commit `f782107` (14 Nov 2026; merge commit approved for this PR, D30) | PR runs 43632886441 and 43632892000 ✅; `main` run 43633165321 ✅ (all four jobs) |
| **PR3.2** — AI Core Foundation | `c90b418` | PR #10, merge commit `1bad661` (14 Nov 2026; merge commit approved for this PR, D39) | PR runs 43642841055 and 43642849992 ✅; `main` run 43643259648 ✅ (all four jobs) |
| **PR3.3** — Persistent AI Memory & Knowledge | `87ea2cb` | PR #12, merge commit `39ae4ab` (14 Nov 2026; merge commit approved for this PR, D44) | PR runs 43649601040 and 43649605521 ✅; `main` run 43650005302 ✅ (all four jobs) |
| **PR3.4** — Agent Framework & Orchestration | `fedb80c` | PR #14, merge commit `93a860a` (15 Nov 2026; merge commit approved for this PR, D53) | PR runs 43747356816 and 43747362677 ✅; `main` run 43747844740 ✅ (all four jobs) |

All PR2.x merges took place on 14 November 2026. Branch-level CI runs are listed in [ROADMAP.md](ROADMAP.md#phase-2--platform-foundations--complete).

**Phase 1 historical note (verified 14 November 2026):**
- The v0.3–v0.7 prototype existed, but the repository history doesn't represent each version individually.
- The prototype entered the repository as one commit, `87c1b04` "Created Frontend" (4 November 2026), after `36390ac` "Initial commit". Four housekeeping commits followed (`4cf01e7`, `f0046e5`, `13a5bf6`, `d3acf5f`).
- The recorded Phase 1 history ends at `d3acf5f` "Update .gitignore" on 4 November 2026.
- `README.md` at `d3acf5f` still said "v0.3", but the code there already contains the v0.4–v0.7 features.

## Repository state: verification results (14 November 2026)

These were true when checked. Re-check before relying on them.

- **`main`:** `45ca3df` "Merge pull request #15 …" (the PR3.4 status update), the GitHub default branch.
- **CI on `main` at `45ca3df`:** run 44789150559 passed:
  - frontend lint, types, tests and build;
  - backend lint, types and tests (real PostgreSQL, PostgreSQL 18 client tools installed);
  - end-to-end (browser + API + PostgreSQL);
  - container smoke test.
- **Pull requests:** PRs #1–#15 were merged. None open.
- **Branches:**
  - `main`;
  - `phase-3/pr3.0-booski-blueprint`, merged through PR #6, still present on GitHub and locally;
  - `phase-3/pr3.0-status-complete`, merged through PR #7, still present on GitHub and locally;
  - `phase-3/pr3.1-ccgs-audit`, merged through PR #8, still present on GitHub and locally;
  - `phase-3/pr3.1-status-complete`, merged through PR #9, still present on GitHub and locally;
  - `phase-3/pr3.2-ai-core-foundation`, merged through PR #10, still present on GitHub and locally;
  - `phase-3/pr3.2-status-complete`, merged through PR #11, still present on GitHub and locally;
  - `phase-3/pr3.3-ai-memory-knowledge`, merged through PR #12, still present on GitHub and locally;
  - `phase-3/pr3.3-status-complete`, merged through PR #13, still present on GitHub and locally;
  - `phase-3/pr3.4-agent-framework`, merged through PR #14, still present on GitHub and locally;
  - `phase-3/pr3.4-status-complete`, merged through PR #15, still present on GitHub and locally;
  - `phase-3/pr3.5-tools-execution`, created from `45ca3df`; local only, holding PR3.5;
  - five merged `phase-2/*` branches, still present on GitHub and locally (PROP-2).
- **Branch protection on `main`:** **on** since 14 November 2026 (D25): the four CI jobs are required, force-pushes and deletion are blocked, and the rules apply to administrators.
- **Test suites on the PR3.5 branch (run locally, 20 November 2026):**
  - 891 backend tests, all passing (854 before PR3.5);
  - 51 frontend unit tests, passing locally and in CI;
  - 14 end-to-end journeys, passing in CI (local runs timed out on page loads under heavy machine load on 14 November);
  - the container smoke test in CI.
- **Development database:** upgraded to migration 0005 on 15 November 2026 (with the human's approval) for the live key test; it will need `booski db upgrade` again for 0006.
- **Live key test:** a workspace-scoped key is in `backend/.env`; the call was refused for low Anthropic credit. Parked until the human adds credit.

## Outstanding reviews

- **PR3.5:** built, tested locally and committed on `phase-3/pr3.5-tools-execution`; awaiting the human's review. No push, PR or merge without explicit approval.

## Blockers

- None.
- Before any external (non-localhost) deployment, the checklist in `backend/DEPLOYMENT.md` applies: HTTPS, trusted proxy, rate limiting, MFA or SSO, monitoring and backups.

## Outstanding decisions

| Question | Where it's tracked |
|---|---|
| Delete the five merged Phase 2 branches? (The merged PR3.0 and PR3.1 branches also remain; PROP-2 doesn't cover them yet.) | PROP-2, [DECISIONS.md](DECISIONS.md#prop-2--delete-merged-phase-2-branches) |
| How and when is file storage built, and in which milestone? | [ROADMAP.md](ROADMAP.md#open-cross-cutting-requirements) |
| Where does the integrations module go? | [ROADMAP.md](ROADMAP.md#open-cross-cutting-requirements) |
| When are MFA or SSO, email invitations, scheduled backups, metrics export and multi-instance session cleanup built? | [ROADMAP.md](ROADMAP.md#open-cross-cutting-requirements) |
| The proposed mapping of unbuilt Phase 2 plan items to Phase 3 milestones | [ROADMAP.md](ROADMAP.md#phase-2--platform-foundations--complete) |
| Acceptance criteria for PR3.2–PR3.8 are proposed; confirm each when its milestone is planned | [ROADMAP.md](ROADMAP.md#phase-3--ai-core--workforce--in-progress) |
| Should the PR2.x implementation choices (D18–D20, D23) be confirmed as standing decisions? | [DECISIONS.md](DECISIONS.md) |
| Historical gaps (see list below) | [DECISIONS.md](DECISIONS.md) |

**Historical gaps:**
- reasoning for D5, D7, D9 and D10;
- reasoning for D11 beyond usage;
- the options offered for D16;
- the reasoning for, and any approval of, the PR2 re-scoping (D17);
- who chose seven default departments, and why (D21);
- the exact dates of the PR2.3 implementation choices (D18, D21).

## Next recommended action

1. The human reviews PR3.5. If approved, and only with explicit approval for each step: push, open a PR, wait for CI, merge using the approved strategy, then mark PR3.5 **Complete** in a follow-up PR.
2. **Live key test, parked:** once the human adds Anthropic credit, run `booski ai check` once (a fraction of a cent). The key is already in `backend/.env`.
3. Optionally decide PROP-2 (the merged Phase 2 and Phase 3 branches remain).
4. Only if the human asks: plan PR3.6 (Booski Local Worker). It starts only on explicit approval. It needs a separate security review before merge (ROADMAP). Check D15 (HTTPS long-polling with leases), D28 and D29 (Unity version per project).

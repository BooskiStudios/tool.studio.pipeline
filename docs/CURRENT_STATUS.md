# Booski Studios — Current Status

> **What this document is:** the actual state of the project as last verified. Update it whenever the real state changes (a merge, a new branch, CI results, a decision) in the same branch as the change.
>
> **Last verified:** 14 November 2026, after PR3.1 was merged (PR #8), while preparing the follow-up status update on branch `phase-3/pr3.1-status-complete`.
>
> The Git, PR and CI facts below are **results of that verification, not guarantees about the present**. Every new session must re-check them before relying on them:
> - `git status`, `git branch -a`, `git log origin/main -5`;
> - `gh pr list --state all`, `gh run list --branch main --limit 5`.
>
> If the live facts disagree with this file, the repository wins: say so, and correct this file.

## Where we are

- **Phase:** Phase 3 — AI Core & Workforce is in progress.
- **No milestone is currently approved.**
- **Last completed milestone:** **PR3.1 — Open-Source Capability Adoption Audit**. Merged into `main` through PR #8 (merge commit `f782107`); CI on `main` passed.
  - Deliverables: [audits/PR3.1-CCGS-AUDIT.md](audits/PR3.1-CCGS-AUDIT.md) and [BOOSKI_GAME_DEV_TOOLKIT.md](BOOSKI_GAME_DEV_TOOLKIT.md). Nothing from CCGS was imported.
  - Decided after review: the toolkit target is Route A, Booski agent configurations (D27); CCGS is acknowledged when inspired features are built (D28); the studio uses Unity 6.3 LTS, with an upgrade expected later (D29). The toolkit's contents remain a proposal.
- **Next milestone:** **PR3.2 — AI Core Foundation**. **Status: Planned.** Not approved, not started. It may start only when the human explicitly approves it, after its plan and acceptance criteria are agreed.
- **What exists today:** a working, persistent, multi-user studio application (Booski Core plus the React interface). It is the **foundation for the future Booski Control Plane**, not the completed Control Plane architecture described in [ARCHITECTURE.md](ARCHITECTURE.md). It stores accounts, workspaces, roles, departments, projects, milestones, tasks, documents, decisions, approvals and activity. The repository also holds the project documentation (`CLAUDE.md` and `docs/`), which is the source of truth for the plan and process.
- **What does not exist:** any AI functionality.
  - AI-related screens (command bar, AI workforce, agents, cost and usage, integrations) are **labelled previews**.
  - No AI provider, model registry, memory system, agent, orchestration, tool execution, Local Worker, Claude Code integration or file storage has been built.

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

All PR2.x merges took place on 14 November 2026. Branch-level CI runs are listed in [ROADMAP.md](ROADMAP.md#phase-2--platform-foundations--complete).

**Phase 1 historical note (verified 14 November 2026):**
- The v0.3–v0.7 prototype existed, but the repository history doesn't represent each version individually.
- The prototype entered the repository as one commit, `87c1b04` "Created Frontend" (4 November 2026), after `36390ac` "Initial commit". Four housekeeping commits followed (`4cf01e7`, `f0046e5`, `13a5bf6`, `d3acf5f`).
- The recorded Phase 1 history ends at `d3acf5f` "Update .gitignore" on 4 November 2026.
- `README.md` at `d3acf5f` still said "v0.3", but the code there already contains the v0.4–v0.7 features.

## Repository state: verification results (14 November 2026)

These were true when checked. Re-check before relying on them.

- **`main`:** `f782107` "Merge pull request #8 …" (PR3.1), the GitHub default branch.
- **CI on `main` at `f782107`:** run 43633165321 passed:
  - frontend lint, types, tests and build;
  - backend lint, types and tests (real PostgreSQL, PostgreSQL 18 client tools installed);
  - end-to-end (browser + API + PostgreSQL);
  - container smoke test.
- **Pull requests:** PRs #1–#8 were merged. This status update is a follow-up docs-only PR from `phase-3/pr3.1-status-complete`.
- **Branches:**
  - `main`;
  - `phase-3/pr3.0-booski-blueprint`, merged through PR #6, still present on GitHub and locally;
  - `phase-3/pr3.0-status-complete`, merged through PR #7, still present on GitHub and locally;
  - `phase-3/pr3.1-ccgs-audit`, merged through PR #8, still present on GitHub and locally;
  - `phase-3/pr3.1-status-complete`, this follow-up status update;
  - five merged `phase-2/*` branches, still present on GitHub and locally (PROP-2).
- **Branch protection on `main`:** **on** since 14 November 2026 (D25): the four CI jobs are required, force-pushes and deletion are blocked, and the rules apply to administrators.
- **Test suites** (unchanged by PR3.0 and PR3.1, which are documentation only):
  - 574 backend tests (counted with `pytest --collect-only` at `a68d829`);
  - 51 frontend unit tests (from the last full Vitest run);
  - 14 end-to-end journeys;
  - the container smoke test in CI.

## Outstanding reviews

- None. This status update is the docs-only follow-up the human approved with the PR3.1 merge (D30); it is merged with a merge commit once its CI passes.

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

1. Confirm that CI on `main` passed after this status update was merged (`gh run list --branch main --limit 1`).
2. Optionally decide PROP-2 (the merged Phase 2, PR3.0 and PR3.1 branches remain).
3. Only if the human asks: plan PR3.2 (AI Core Foundation). Review its objectives in ROADMAP.md, propose an approach, branch name and acceptance criteria, and check D28 (acknowledge CCGS if the milestone builds anything CCGS-inspired). It starts only on explicit approval.

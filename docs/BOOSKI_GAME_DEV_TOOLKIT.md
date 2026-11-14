# Booski Game Development Toolkit — Proposed Specification

> **Status: PROPOSAL. Not agreed, not built.** Produced by PR3.1 from the [CCGS audit](audits/PR3.1-CCGS-AUDIT.md). Nothing here is authorised until the human approves it, and each part is confirmed again when the milestone that would build it (PR3.2–PR3.8, Phases 4–7) is planned.
>
> **What it is:** the proposed set of agents, workflows, review steps, guardrails, templates and repository guidance that Booski's AI workforce would use for game development, and how each maps onto Booski's architecture.
>
> **What it is not:** an implementation plan, an import of CCGS, or a change to anything that exists today.

## 1. Target form (decided: D27)

The human chose Route A on 14 November 2026 (D27), as the audit recommended ([audit §7](audits/PR3.1-CCGS-AUDIT.md#7-the-two-routes-assessment-and-recommendation)):

- **Primary form: Booski agent configurations and workflows (Route A).** The toolkit is defined as Booski data and configuration, run by Booski's orchestrator (PR3.4), with tools, permissions and approvals enforced server-side (PR3.5).
- **Derived output: a repository guidance pack (Route B, derived).** In PR3.7, Booski generates a small `.claude/` pack for each game repository from its own definitions: instructions, Unity rules and a deny list, for Claude Code sessions run through the Local Worker.

The rest of this specification follows that decision. The **contents** below remain proposals.

## 2. Principles carried into the toolkit

Each principle comes from the audit and is consistent with already-agreed direction:

1. **The human decides.** AI reviews produce *advisory* verdicts; only a human approval is binding (D-P3-3, D-P3-6).
2. **Enforce, don't request.** Anything that must always hold (approvals, forbidden commands, protected paths, delegation limits) is enforced by Booski, not written into a prompt. CCGS's own rules reference makes the same point: rules are "context, not enforcement".
3. **"Not assessed" is never "approved".** Every check and review can report that it didn't run or lacked an input, and that result never counts as a pass.
4. **Outputs are contracts.** A workflow step that declares an output and doesn't produce it has failed, whatever its message says.
5. **An unanswered question is not an answer.** Pending approvals stay pending.
6. **Tools report observations; reviewers and humans judge.**
7. **Cheapest adequate model.** Routine lookups use the cheapest tier; multi-document synthesis and high-stakes reviews use the top tier (D-P3-13).
8. **Unity first, versions pinned per project.** The studio uses Unity 6.3 LTS and expects to upgrade later (D29). The Unity version is a project setting; engine guidance is checked against the project's version, and anything not verified there is marked unverified (D-P3-7).

## 3. Agent definition (proposed fields for PR3.4)

A Booski agent is a configuration record, not a separate AI system (D-P3-3). The proposed fields:

| Field | Purpose | Inspired by (CCGS) |
|---|---|---|
| `key`, `name`, `description` | Identity | Agent front matter |
| `department` | One of Booski's seven departments | Roster tiers |
| `tier` | `lead` or `specialist` (with an optional `parent` agent) | Three-tier hierarchy |
| `responsibilities` | What the agent owns | "Core responsibilities" |
| `must_not` | Explicit limits | "What this agent must NOT do" |
| `delegates_to`, `escalates_to`, `consults` | Allowed delegation and escalation targets, **enforced** by the orchestrator | Delegation maps, coordination rules |
| `tools` | Allowed tool keys from the PR3.5 tool registry (for example, no shell for design roles) | Per-agent tool lists and shell bans |
| `autonomy_ceiling` | Highest autonomy level the agent may run at: Assist, Execute with approval, Controlled autonomy, Coordinated workflows | Automation modes |
| `always_ask` | Action categories that always require human approval, whatever the level | `automation_always_ask` |
| `model_tier` | `routine`, `standard` or `deep`, resolved by PR3.2's model routing per provider | Model tiers |
| `memory_scopes` | Which PR3.3 memory the agent may read and write (workspace, project, department) | `memory: project` |
| `output_contract` | What a run must produce (document kind, task update, decision, review verdict) | Return contracts, `validate-agent-artifact` |
| `turn_limit`, `budget` | Step and cost limits | `maxTurns` |
| `guidance` | The agent's domain guidance text (Booski's own words; attributed where CCGS text is reused) | Agent bodies |

**Shared behaviour isn't duplicated per agent.** The collaboration protocol, version awareness and the "ask before acting" behaviour live once in the orchestrator, not in every definition.

## 4. Proposed initial roster

The agents are introduced in **waves**, tied to the phase that needs them. Names are proposals.

**Wave 1: Game Development and Quality (Phase 4; first defined once PR3.4 exists)**

| Agent | Department | Tier | Parent | Default autonomy ceiling |
|---|---|---|---|---|
| Producer | Studio Operations | Lead | — | Execute with approval |
| Technical Director | Game Development | Lead | — | Assist |
| Lead Programmer | Game Development | Lead | Technical Director | Execute with approval |
| Unity Specialist | Game Development | Specialist | Lead Programmer | Execute with approval |
| Gameplay Programmer | Game Development | Specialist | Lead Programmer | Execute with approval |
| Unity UI Specialist (merges CCGS's UI programmer) | Game Development | Specialist | Unity Specialist | Execute with approval |
| Unity Addressables Specialist | Game Development | Specialist | Unity Specialist | Execute with approval |
| Tools Programmer | Game Development | Specialist | Lead Programmer | Execute with approval |
| Performance Analyst | Game Development | Specialist | Lead Programmer | Assist |
| DevOps Engineer (Unity builds and CI) | Game Development | Specialist | Technical Director | Execute with approval |
| QA Lead | Quality & Oversight | Lead | — | Execute with approval |
| QA Tester | Quality & Oversight | Specialist | QA Lead | Execute with approval |

**Wave 2: Concept Lab and Asset Production (Phase 5)**

| Agent | Department |
|---|---|
| Creative Director (lead) | Concept Lab |
| Game Designer, Systems Designer, Level Designer, Economy Designer | Concept Lab |
| Narrative Director, Writer, World Builder | Concept Lab |
| UX Designer, Prototyper | Concept Lab |
| Accessibility Specialist | Quality & Oversight |
| Art Director (lead), Technical Artist, Unity Shader Specialist | Asset Production |
| Audio Director, Sound Designer | Asset Production |
| AI Programmer | Game Development |

**Wave 3: Operations, Marketing and Post-Launch (Phases 6–7)**

| Agent | Department |
|---|---|
| Release Manager | Studio Operations |
| Community Manager | Marketing Studio / Post-Launch Intelligence |
| Live-Ops Designer, Analytics Engineer | Post-Launch Intelligence |

**Not planned now:** engine programmer, network programmer, security engineer, localisation lead, Unity DOTS specialist (unless a project needs it), and all Godot and Unreal agents. Revisit triggers are in [audit §5.3](audits/PR3.1-CCGS-AUDIT.md#53-agents-all-49).

## 5. Workflows

Workflows are multi-step plans run by the PR3.4 orchestrator. Each step names its agent, inputs, output contract and any review or approval.

**How they map onto Booski records** (all of these exist today):

| Workflow output | Booski record |
|---|---|
| Design documents, specs, reports, checklists | `documents` (kinds `design_doc`, `report`, `template`, `research`) |
| Architecture decisions (ADRs) | `decisions` (proposed → accepted, supersede flow) |
| Epics and stories | `milestones` and `tasks` (with acceptance criteria in the task) |
| Gates and sign-offs | `approvals` (kinds `ai_output`, `code_change`, `asset`, `publishing`, `spending`, `project_decision`) |
| History | `activity_events` (append-only) |

**Proposed first workflows (Phase 4):**

| Workflow | Steps (summary) | Source idea |
|---|---|---|
| **Document an existing Unity project** | Inspect the repository → draft architecture and design documents → human review | `reverse-document` |
| **Architecture decision** | Draft ADR → Technical Director review (advisory) → human accepts in the decisions module | `architecture-decision`, `TD-ADR` |
| **Plan a milestone** | Milestone → tasks with acceptance criteria → readiness check per task → human approval | `create-epics`, `create-stories`, `story-readiness`, `QL-STORY-READY` |
| **Implement a task** | Claude Code implements with tests through the Local Worker → automated checks → Lead Programmer review (advisory) → acceptance-criteria verification → human approves the diff → commit only on approval | `dev-story`, `LP-CODE-REVIEW`, `story-done`, PR3.7 |
| **Milestone review** | Progress, risk, scope check and retrospective → human decision | `milestone-review`, `scope-check`, `retrospective` |
| **QA cycle** | QA plan → test cases → smoke check → test evidence review → sign-off | `team-qa`, `qa-plan`, `smoke-check`, `test-evidence-review` |

Later phases add the design, asset, release and live-ops workflows listed in [audit Appendix A](audits/PR3.1-CCGS-AUDIT.md#appendix-a-skill-by-skill-classification).

## 6. Reviews and approvals

- **AI review step:** a reviewer agent returns one of `approve`, `concerns`, `reject` or `not_assessed`, with reasons and any missing inputs. When several reviewers run, the **strictest** result is shown.
- **Human approval:** the binding decision, recorded through Booski's existing approvals and reviews (append-only). A `concerns` result gives the human three choices: revise, accept and proceed, or discuss.
- **Review intensity per project:** `full` (all reviews), `lean` (stage transitions only) or `solo` (none). Human approvals required by D-P3-6 apply in every mode.
- **Stage checklists:** the artefacts and reviews each project stage expects, based on CCGS's seven stages, mapped onto Booski's existing project statuses. Changing those statuses would be a separate, approved schema change.

## 7. Guardrails (for PR3.5 and PR3.7)

| Guardrail | Enforced where |
|---|---|
| Never-allowed operations: recursive deletes, force-push, `git reset --hard`, `git clean -f`, `sudo`, `chmod 777`, reading or writing `.env` files (Bash and PowerShell variants) | Tool policy and Local Worker; also written into the repository pack's Claude Code settings |
| Approval required: commit, push, merge, tag, release, store uploads (Steam, itch), publishing, spending, external posts | Tool registry (D-P3-6) |
| Nothing upstream: no issues or PRs in engine, plugin or vendor repositories; drafts only | Tool policy |
| Protected paths: files a workflow must never overwrite | Tool policy per project |
| Output contracts: a step without its declared output fails | Orchestrator |
| Limits: turns, time, cost per run | Orchestrator and PR3.2 cost tracking |

## 8. Repository guidance pack (derived output, PR3.7)

Generated by Booski for each Unity repository it works on. Proposed contents:

1. **`CLAUDE.md`:** the project's context from Booski (stage, current task, acceptance criteria), the collaboration rules, and "nothing upstream".
2. **Unity rules:**
   - **Scene and asset files:** never hand-edit `.unity`, `.prefab` or `.asset` YAML while the Editor may have it open; never invent GUIDs; never touch `.meta` files.
   - **Code guidance:** gameplay, core, AI and UI code guidance, plus test standards.
   - **Engine practice:** Unity best practice (composition, ScriptableObjects, assembly definitions, no `Find`/`SendMessage`, no allocations in hot paths, Addressables, the new Input System).
   - **Version check:** check the pinned Unity version before using an API, and mark unverified APIs.
3. **The deny list** from section 7, as Claude Code settings.
4. **The control manifest:** per-system must-do and never-do rules, generated from the project's accepted decisions.
5. **Attribution:** the MIT notice wherever CCGS-derived text is included.

**Unity commands to define in Phase 4:** batch-mode build, Unity Test Framework (Edit Mode and Play Mode) runs, and a smoke check. Unity licensing in CI needs a secrets decision.

## 9. Supporting capabilities

| Capability | Milestone | Notes |
|---|---|---|
| Model tiers (`routine` / `standard` / `deep`) mapped per provider | PR3.2 | Provider-agnostic aliases, not model IDs. |
| Context assembly (project stage, milestone, recent activity, relevant decisions) | PR3.3 | Replaces CCGS's session-start hook and checkpoint file. |
| Memory-quality rule: a temporary absence is never stored as a durable fact | PR3.3 | From CCGS's agent-memory rule. |
| Agent evaluation: behavioural specs per agent and workflow, a rubric, re-run when a definition changes | PR3.4 | From CCGS's studio tests and `skill-test`. |
| Run audit trail and cost per run | PR3.2, PR3.4 | Replaces CCGS's log hooks and spawn tally. |
| Command Centre "next step" and stage detection | PR3.8 | From `next-step` and `project-stage-detect`. |
| Templates: concept, design, technical, production, QA and release | Phases 4–6 | Booski `template` documents; section structure informed by CCGS; wording Booski's own. |
| Unity version reference | Phase 4 | Booski's own, starting with Unity 6.3 LTS (D29) and scoped per version so upgrades are deliberate; CCGS's content not reused. |

## 10. Licence and attribution

Follow [audit §8](audits/PR3.1-CCGS-AUDIT.md#8-licence-obligations):
- **Ideas and structure:** rewritten in Booski's words, with an acknowledgement.
- **Substantial reused text:** recorded in `THIRD_PARTY_NOTICES.md` with the MIT text, source path and pinned commit, and marked at the point of use.
- **The repository pack:** carries the notice where it includes CCGS-derived text.

## 11. Decisions this specification needs

1. **Route:** decided, Route A (D27).
2. **Acknowledgements note:** decided, added when CCGS-inspired features are built (D28).
3. **Wave 1 roster and default autonomy ceilings:** confirm when PR3.4 is planned.
4. **Workflow list for Phase 4:** confirm when Phase 4 is planned.
5. **Unity version:** decided, Unity 6.3 LTS, with an upgrade expected later (D29). How Booski supports an upgrade is open (Phase 4).
6. **Project stages:** whether CCGS's finer stages should change Booski's project statuses (a later schema change).

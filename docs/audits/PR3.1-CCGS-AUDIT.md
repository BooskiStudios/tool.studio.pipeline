# PR3.1 — Open-Source Capability Adoption Audit: Claude Code Game Studios

> **What this document is:** the PR3.1 audit of [`Donchitos/Claude-Code-Game-Studios`](https://github.com/Donchitos/Claude-Code-Game-Studios) ("CCGS"). It classifies each capability area as **reuse, adapt, rebuild or ignore**, with reasons.
>
> **Status:** findings and recommendations only. Every recommendation here is a **proposal** awaiting the human's decision. **Nothing from CCGS has been imported** into this repository, and nothing in this document is built.
>
> The proposed specification that follows from it is [BOOSKI_GAME_DEV_TOOLKIT.md](../BOOSKI_GAME_DEV_TOOLKIT.md).

## 1. Summary

- **What CCGS is:** a *template repository for Claude Code*, not a library or service. All of it is Claude Code configuration: 49 agent definitions, 78 skill folders, 18 hook scripts, 14 path-scoped rules, about 65 document templates, 28 review-gate definitions, and supporting docs and scripts. You clone it and run Claude Code inside it.
- **Strongest overlap with Booski:** CCGS's collaboration protocol is the same **Question → Options → Decision → Draft → Approval** pattern Booski adopted in PR3.0 (D-P3-3). Its review gates, automation modes, model tiers and destructive-command deny list address the same problems as Booski's approvals (D-P3-6), autonomy levels, cost principles (D-P3-13) and tool guardrails (PR3.5).
- **Biggest difference:** CCGS enforces almost everything through **prompt text and warn-only hooks inside one Claude Code session**. Its own rules reference says rules are "context, not enforcement". Booski's principles require permissions, approvals and audit to be **enforced server-side and recorded** (CLAUDE.md §8, D-P3-6). So CCGS's *content and patterns* are valuable, but its *mechanisms* must mostly be rebuilt.
- **Unity fit is partial:** CCGS's default route is a browser game, and its most-developed engine route is Godot. It has a solid Unity lead agent and four Unity sub-specialists, but **no Unity run, build or test commands** in its engine table, and its own README says the engine routes are "not yet shown" in testing.
- **Recommended route (proposal; the human decides):** target **Route A, Booski agent configurations** (PR3.4) as the toolkit's primary form, and derive a small, Booski-generated `.claude/` guidance pack for game repositories in PR3.7 (Route B as a *derived output*, not CCGS's toolkit installed wholesale). The reasoning is in [§7](#7-the-two-routes-assessment-and-recommendation).
- **Licence:** MIT, "Copyright (c) 2026 Donchitos". Reusing any substantial text requires keeping that notice and the permission text (see [§8](#8-licence-obligations)).

## 2. Source and method

| Item | Value |
|---|---|
| Repository | `Donchitos/Claude-Code-Game-Studios` (public) |
| Pinned commit | `abc0de79d6ceb0b5d7aa693945849b3937afbe6a`, "Release 1.3.0 — make me a game", 9 November 2026 |
| Licence | MIT, "Copyright (c) 2026 Donchitos" |
| Size at the pin | 794 tracked files, about 12 MB |
| Release cadence | Six releases between 23 September and 9 November 2026 (v1.1.0–v1.3.0) |
| Audited | 14 November 2026 |

**How it was read:**
- The repository was fetched at the pinned commit into a temporary folder **outside** this repository. Nothing from it was run, installed or copied in.
- **Read in full:** the root `CLAUDE.md`, `LICENSE`, the README's opening sections, the agent roster, the coordination rules, the director-gates index, the model-tier and automation-mode documents (key sections), the hooks reference, the rules reference, `.claude/settings.json` (permissions and hook wiring), `project.yaml`, and the Unity lead agent (`unity-specialist`).
- **Read in part:** each of the 49 agents' front matter (tools, model, turn limits, memory); the section structure of the four Unity sub-specialists; the Unity engine reference index and `VERSION.md`; the headings of the collaborative-design principle and the workflow catalogue; the studio-tests README; the agent-memory rule.
- **Read by description only:** each of the 78 skills (front matter description and model), the 28 gate definitions (index entries), and the template file names.
- **Not done:** reading every hook script, skill body or gate definition line by line; running or testing anything. Classifications based on descriptions say so where it matters, and should be re-checked before any item is actually reused.

**Short quotations** from CCGS appear in quotation marks for accuracy. No substantial CCGS text is reproduced.

## 3. Inventory at the pinned commit

| Area | Location in CCGS | Count |
|---|---|---|
| Agent definitions | `.claude/agents/` | 49 (3 leadership, 8 department leads, 23 specialists, 3 engine leads, 12 engine sub-specialists) |
| Skills (slash-command workflows) | `.claude/skills/` | 78 folders, including 3 old-name aliases (`changelog`, `help`, `settings`). The README's "72 workflow skills" counts differently. |
| Hooks | `.claude/hooks/` + wiring in `.claude/settings.json` | 18 files (15 wired hooks, plus `log-instructions.sh` (optional), `update-check.sh` and the `yaml-helper.sh` library) |
| Path-scoped rules | `.claude/rules/` | 14 |
| Review gates | `.claude/docs/director-gates/` | 28 |
| Document templates | `.claude/docs/templates/` | 65 entries (63 files, 2 subfolders) |
| Production stages | `.claude/docs/workflow-catalog.yaml` | 7 stages plus a "minimal path" |
| Permission policy | `.claude/settings.json` | Ask-first default mode; a long deny list (recursive delete, force-push, hard reset, `git clean -f`, `sudo`, `.env` reads, Unreal binary edits) |
| Framework tests | `studio-tests/` | Specs for skills and agents, a catalogue and a quality rubric |
| Engine data | `.claude/engines/`, `docs/engine-reference/` | An engine table (Web, Godot, Unity, Unreal) and version-pinned engine notes |
| Genre data | `.claude/genres/` | 74 files |
| Scripts | `.claude/scripts/` | 54 helper scripts ("observations, never verdicts") |

## 4. Classification key

| Class | Meaning in this audit |
|---|---|
| **Reuse** | Take the material largely as it is (with attribution). |
| **Adapt** | Keep the idea or structure, rewrite it for Booski's architecture (agents as configurations, server-side permissions, PostgreSQL records). Any substantial text reused keeps attribution. |
| **Rebuild** | The need is real, but CCGS's mechanism doesn't fit Booski; build Booski's own from scratch. |
| **Ignore** | Not needed, or **not now** (with a revisit trigger). |

The **Phase** column says when the item would matter, following the [roadmap](../ROADMAP.md): PR3.x milestones, or Phases 4–7.

## 5. Classification by capability area

### 5.1 Collaboration protocol and automation modes

| Item | Class | Phase | Reason |
|---|---|---|---|
| Collaboration protocol (Question → Options → Decision → Draft → Approval; ask before writing a named path; show drafts first; no commits without instruction) | **Adapt** | PR3.4, PR3.5 | Already Booski's agreed principle (D-P3-3). In CCGS it is prompt text; in Booski the "ask before writing" step should be an enforced approval (`ai_output`, `code_change`), not a request in the prompt. |
| "A skipped or dismissed question is not an answer" | **Adapt** | PR3.4 | A sound rule for agent runs: an unanswered approval stays pending, it never defaults to yes. |
| Automation modes: `collaborative` / `guided` / `autonomous`, major-versus-minor decision classes, "always ask" categories, a decision log in autonomous mode | **Adapt** | PR3.4, PR3.5 | Maps onto Booski's four autonomy levels (Assist, Execute with approval, Controlled autonomy, Coordinated workflows). The "always ask" categories and the decision log are directly useful. The levels must be enforced by Booski's permission checks, not chosen inside a prompt. |
| Orchestrated-run exception (a subagent may write a new file at a path its orchestrator named, without a separate prompt) | **Adapt (with care)** | PR3.4 | A practical idea: approval of a plan can cover its named outputs. In Booski this needs an explicit, recorded approval scope, not an implicit exception. |

### 5.2 Agent hierarchy and coordination

| Item | Class | Phase | Reason |
|---|---|---|---|
| Three tiers (leadership → department leads → specialists) with engine leads and sub-specialists | **Adapt** | PR3.4 | Matches Booski's department model. Booski's tiers should map to its seven departments rather than CCGS's discipline split. |
| Coordination rules: vertical delegation, horizontal consultation, escalation to a shared parent, no cross-domain changes, change propagation through the producer | **Adapt** | PR3.4 | Good orchestration rules. In CCGS, an agent "keeping to it is up to you"; Booski should enforce delegation targets and tool scopes in the orchestrator. |
| "Nothing goes upstream" (never file issues or PRs in vendor repositories; draft only) | **Adapt** | PR3.5 | Matches D-P3-6 (publishing and significant external actions need approval). Becomes a tool policy. |
| Subagents versus experimental agent teams | **Ignore** | — | Claude Code session mechanics. Booski's orchestration (PR3.4) replaces both. |
| Parallel-task protocol (spawn independent work together, surface blocked agents, always produce a partial report) | **Adapt** | PR3.4 | Directly useful behaviour for multi-agent runs. |

### 5.3 Agents (all 49)

**Department** is the proposed Booski home; the PR3.0 vision defines the seven departments.
**Front matter** summarises CCGS's own settings: model pin, turn limit, and whether shell access is disallowed.

**Tier 1: leadership**

| Agent | Department | Class | Phase | Notes |
|---|---|---|---|---|
| `creative-director` | Concept Lab | **Adapt** | 5 | Opus; 30 turns; no shell. Holds vision and pillars; resolves design conflicts. |
| `technical-director` | Game Development | **Adapt** | 4 | Opus; 30 turns. Architecture and technical risk; escalation target for technical conflicts. |
| `producer` | Studio Operations | **Adapt** | 4 | Opus; 30 turns. Scope, sprints, milestones, change propagation. Maps onto Booski's projects, milestones and tasks. |

**Tier 2: department leads**

| Agent | Department | Class | Phase | Notes |
|---|---|---|---|---|
| `game-designer` | Concept Lab | **Adapt** | 5 | Mechanics, systems and balance; no shell. |
| `lead-programmer` | Game Development | **Adapt** | 4 | Sonnet. Code architecture and review; owns the `LP-CODE-REVIEW` gate. |
| `art-director` | Asset Production | **Adapt** | 5 | Style guides and the art bible; no shell. |
| `audio-director` | Asset Production | **Adapt** | 5 | No shell. Lower priority for a small studio. |
| `narrative-director` | Concept Lab | **Adapt** | 5 | No shell. Story and world consistency. |
| `qa-lead` | Quality & Oversight | **Adapt** | 4 | Test strategy, bug triage, release readiness. |
| `release-manager` | Studio Operations | **Adapt** | 6 | Builds, versions, changelogs, rollbacks. |
| `localization-lead` | Marketing Studio | **Ignore (not now)** | — | Revisit when a game needs translation. |

**Tier 3: specialists**

| Agent | Department | Class | Phase | Notes |
|---|---|---|---|---|
| `systems-designer` | Concept Lab | **Adapt** | 5 | Formulas, loops, mechanics detail. |
| `level-designer` | Concept Lab | **Adapt** | 5 | Layout and pacing. |
| `economy-designer` | Concept Lab | **Adapt** | 5 | Economies, loot, progression curves. |
| `gameplay-programmer` | Game Development | **Adapt** | 4 | Core implementation agent for Unity work. |
| `engine-programmer` | Game Development | **Ignore (not now)** | — | Engine-internals work is rare on Unity. Revisit for custom low-level systems. |
| `ai-programmer` | Game Development | **Adapt** | 4–5 | Behaviour trees, pathfinding, NPC logic. |
| `network-programmer` | Game Development | **Ignore (not now)** | — | Revisit for a multiplayer project. |
| `tools-programmer` | Game Development | **Adapt** | 4 | Unity editor extensions and pipeline tools. |
| `ui-programmer` | Game Development | **Adapt (merge)** | 4 | Overlaps `unity-ui-specialist`; merge into one Unity UI role. |
| `technical-artist` | Asset Production | **Adapt** | 5 | Shaders, VFX, art pipeline. |
| `sound-designer` | Asset Production | **Adapt** | 5 | No shell; 10 turns. |
| `writer` | Concept Lab | **Adapt** | 5 | Dialogue and lore; also useful for Marketing copy. |
| `world-builder` | Concept Lab | **Adapt** | 5 | World rules and lore. |
| `qa-tester` | Quality & Oversight | **Adapt** | 4 | Test cases, bug reports; the longest turn limit (60). |
| `performance-analyst` | Game Development | **Adapt** | 4 | Profiling and budgets. |
| `devops-engineer` | Game Development | **Adapt** | 4 | Sonnet. Unity build automation and CI. |
| `analytics-engineer` | Post-Launch Intelligence | **Adapt** | 7 | Telemetry and dashboards. |
| `ux-designer` | Concept Lab | **Adapt** | 5 | Flows, wireframes, input, accessibility. |
| `prototyper` | Concept Lab | **Adapt** | 5 | Sonnet. CCGS's version leans to browser one-shots; Booski needs Unity prototypes too. |
| `security-engineer` | Quality & Oversight | **Ignore (not now)** | — | Anti-cheat and save security. Revisit for online or competitive games. |
| `accessibility-specialist` | Quality & Oversight | **Adapt** | 5 | Accessibility requirements and checks. |
| `live-ops-designer` | Post-Launch Intelligence | **Adapt** | 7 | Seasons, events, retention. |
| `community-manager` | Marketing Studio / Post-Launch | **Adapt** | 6–7 | Sonnet; no shell. Patch notes, player feedback, community comms. |

**Engine leads and sub-specialists**

| Agent | Department | Class | Phase | Notes |
|---|---|---|---|---|
| `unity-specialist` | Game Development | **Adapt (priority)** | 4 | Reviewed in depth ([§6](#6-unity-in-depth)). High-quality Unity guidance. |
| `unity-ui-specialist` | Game Development | **Adapt** | 4 | UI Toolkit versus UGUI, data binding, input, accessibility. |
| `unity-addressables-specialist` | Game Development | **Adapt** | 4 | Asset loading, memory, content updates. |
| `unity-shader-specialist` | Asset Production | **Adapt** | 5 | Shader Graph, VFX Graph, URP/HDRP. |
| `unity-dots-specialist` | Game Development | **Adapt (when needed)** | 4+ | Only for projects that need ECS-scale performance. |
| `godot-specialist`, `godot-gdscript-specialist`, `godot-csharp-specialist`, `godot-shader-specialist`, `godot-gdextension-specialist` | — | **Ignore (not now)** | — | Booski is Unity-first (D-P3-7). Not reviewed in detail. Revisit if a Godot project is planned. |
| `unreal-specialist`, `ue-gas-specialist`, `ue-blueprint-specialist`, `ue-replication-specialist`, `ue-umg-specialist` | — | **Ignore (not now)** | — | Unreal is "later" (D-P3-7). Not reviewed in detail. Revisit when Unreal support is planned. |

**Patterns shared by all agents:**
- **Collaboration preamble:** every implementer agent repeats the same block (read the design doc, ask, propose, implement transparently, ask "May I write…?", offer next steps). **Adapt:** in Booski this belongs once in the shared orchestration, not copied into every agent.
- **"Must not do" lists and delegation maps** (reports to, delegates to, escalates to, coordinates with): **Adapt** directly into Booski agent configurations; they are the most reusable part of each agent.
- **Per-agent tool lists and shell bans** (writers and designers have no shell; directors have web search): **Adapt** as each agent's allowed tools in Booski's tool registry (PR3.5).
- **Model pins** (3 Opus directors, 16 Sonnet, the rest inherit): **Adapt** as a model-tier field (see [§5.11](#511-other-material)).
- **`memory: project`** on directors and designers: **Adapt** as a memory scope in PR3.3.

### 5.4 Skills and workflows

The 78 skills group into eight families. Each skill's individual classification is in [Appendix A](#appendix-a-skill-by-skill-classification).

| Family | Skills | Class | Phase | Reason |
|---|---|---|---|---|
| Onboarding and navigation | `start`, `next-step`, `help`, `onboard`, `project-stage-detect`, `adopt`, `project-settings`, `settings`, `setup-engine` | **Ignore** (mostly) | — | Booski's interface and data replace them. The *idea* of `project-stage-detect` and `next-step` (derive the stage and the one next action from real data) is worth adapting in Booski's Command Centre (PR3.8). |
| Concept and design | `brainstorm`, `prototype`, `quick-design`, `design-system`, `map-systems`, `design-review`, `review-all-gdds`, `consistency-check`, `propagate-design-change`, `art-bible`, `asset-spec`, `ux-design`, `ux-review`, `reverse-document` | **Adapt** | 5 (some 4) | Strong workflow designs. They become Booski workflows that produce `design_doc` documents and decisions. `reverse-document` is useful early in Phase 4 for existing Unity projects. |
| Architecture | `create-architecture`, `architecture-decision`, `architecture-review`, `create-control-manifest` | **Adapt** | 4 | ADRs map directly onto Booski's existing **decisions** module. The "control manifest" (must-do and never-do rules per system) is a good input for Claude Code instructions in PR3.7. |
| Planning and production | `create-epics`, `create-stories`, `story-readiness`, `dev-story`, `story-done`, `sprint-plan`, `sprint-status`, `estimate`, `scope-check`, `milestone-review`, `retrospective`, `cut`, `content-audit`, `vertical-slice`, `gate-check` | **Adapt** | 4 | Map onto Booski's projects, milestones, tasks and approvals. `dev-story` and `story-done` (implement, then verify each acceptance criterion) are the core loop for Claude Code execution (PR3.7, Phase 4). |
| Quality | `code-review`, `qa-plan`, `regression-suite`, `smoke-check`, `soak-test`, `test-setup`, `test-helpers`, `test-evidence-review`, `test-flakiness`, `bug-report`, `bug-triage`, `balance-check`, `perf-profile`, `security-audit`, `tech-debt`, `asset-audit`, `playtest-report` | **Adapt** | 4 (some 5) | Quality & Oversight workflows. Unity needs its own test runner and CI commands, which CCGS doesn't define (see [§6](#6-unity-in-depth)). |
| Release and live | `release-checklist`, `launch-checklist`, `day-one-patch`, `hotfix`, `patch-notes`, `write-changelog`, `changelog`, `localize` | **Adapt** | 6–7 | Studio Operations, Marketing Studio and Post-Launch work. Store certification templates (Steam, itch) are useful. |
| Team orchestration | `team-audio`, `team-combat`, `team-level`, `team-live-ops`, `team-narrative`, `team-polish`, `team-qa`, `team-release`, `team-ui` | **Rebuild** | PR3.4 | The *pattern* (a named team, ordered phases, review gates between phases) is exactly what PR3.4's multi-step plans need. Each CCGS team is prompt-orchestrated inside one session; Booski's orchestrator should run them as recorded, resumable runs. |
| Framework self-testing | `skill-test`, `skill-improve` | **Rebuild** | PR3.4 | The idea (behavioural specs and a rubric for agents and workflows, with a test-fix-retest loop) should become Booski's agent evaluation. The mechanism is specific to Claude Code skills. |

### 5.5 Production stages

| Item | Class | Phase | Reason |
|---|---|---|---|
| Seven stages: Concept → Systems Design → Technical Setup → Pre-Production → Production → Polish → Release, plus a minimal path | **Adapt** | 4–5 | Booski projects already have a status (`concept`, `pre_production`, `prototype`, `production`, `released`, `paused`, `cancelled`). CCGS's finer stages, and the artefacts each stage needs, can inform stage checklists and gate coverage. Any change to Booski's project statuses would be a schema change needing its own approval. |
| Stage-to-gate coverage table (required and optional gates per stage) | **Adapt** | 4–5 | A good basis for which approvals each Booski project stage expects. |
| `rigor` setting (`minimal` / `standard` / `full`) fronting six knobs | **Adapt** | 4 | A per-project "how much process" setting suits a small studio. In Booski it would be a project setting, not a YAML file. |

### 5.6 Review gates

**Gate pattern:**

| Item | Class | Phase | Reason |
|---|---|---|---|
| Gate pattern: a named reviewer agent, defined inputs, a fixed verdict vocabulary | **Adapt** | PR3.4, PR3.5 | Useful as **AI review steps** that feed Booski approvals. **Important difference:** in CCGS an AI director's verdict decides; in Booski the **human approval is binding** and the AI verdict is advisory evidence. |
| Verdicts APPROVE/READY, CONCERNS, REJECT/NOT READY, **NOT ASSESSED**; strictest verdict wins when several reviewers run | **Adapt** | PR3.4 | "NOT ASSESSED" (a reviewer that couldn't check approves nothing) is an excellent rule for any automated check Booski runs. |
| Review modes `full` / `lean` / `solo` | **Adapt** | 4 | A per-project review-intensity setting. |
| Recording gate outcomes in the document's status header | **Rebuild** | PR3.5 | Booski records reviews in `approval_reviews` and the activity log, which are append-only. |

**Individual gates** (all **Adapt** as advisory AI review steps unless marked; the phase is when they'd be useful):

| Gates | Reviewer | Phase |
|---|---|---|
| `CD-PILLARS`, `CD-GDD-ALIGN`, `CD-SYSTEMS`, `CD-NARRATIVE`, `CD-PLAYTEST`, `CD-PHASE-GATE` | Creative director | 5 |
| `TD-SYSTEM-BOUNDARY`, `TD-FEASIBILITY`, `TD-ARCHITECTURE`, `TD-ADR`, `TD-ENGINE-RISK`, `TD-PHASE-GATE`, `TD-MANIFEST`, `TD-CHANGE-IMPACT` | Technical director | 4 |
| `PR-SCOPE`, `PR-SPRINT`, `PR-MILESTONE`, `PR-EPIC`, `PR-PHASE-GATE` | Producer | 4 |
| `AD-CONCEPT-VISUAL`, `AD-ART-BIBLE`, `AD-PHASE-GATE`, `AD-VISUAL` | Art director | 5 |
| `LP-FEASIBILITY`, `LP-CODE-REVIEW` | Lead programmer | 4 (`LP-CODE-REVIEW` is the priority: it pairs with PR3.7's diff review) |
| `QL-STORY-READY`, `QL-TEST-COVERAGE` | QA lead | 4 |
| `ND-CONSISTENCY` | Narrative director | 5 |

### 5.7 Hooks and the permission policy

CCGS's hooks mostly **warn and never block**. For example, `validate-push.sh` *warns* on pushes to `main`. Booski requires approval for source-control actions (D-P3-6), so most hooks become **enforced policies** in Booski rather than ported scripts.

| Hook | What it does in CCGS | Class | Phase | Booski equivalent |
|---|---|---|---|---|
| `validate-commit.sh` | Checks design-doc sections, JSON data, hard-coded values and TODO format on `git commit` | **Rebuild** | PR3.7 | Pre-approval checks shown with the diff; commits need approval. |
| `validate-push.sh` | Warns on pushes to protected branches, tags, merges and store uploads (`butler`, `steamcmd`) | **Rebuild** | PR3.5, PR3.7 | Push, merge, tag and store upload are approval-gated tools (D-P3-6). Its list of risky commands is a useful checklist. |
| `validate-registry.sh` | Warns on renumbering or deleting registry entries | **Ignore** | — | CCGS-specific YAML registries. |
| `validate-write.sh` | Warns before overwriting files skills never overwrite | **Adapt** | PR3.5 | A "protected paths" list in destructive-action protection. |
| `validate-read.sh` | Blocks whole-file reads of large docs | **Ignore** | — | Claude Code context mechanics; PR3.3's context budget covers the need. |
| `validate-agent-artifact.sh` | Warns when a subagent didn't write the file its contract named | **Adapt** | PR3.4 | A run step that didn't produce its declared output is marked failed, whatever its reply says. |
| `validate-assets.sh` | Checks data JSON and asset naming | **Adapt** | 5 | Asset checks for Asset Production. |
| `session-start.sh` | Loads sprint, milestone, Git activity and the session checkpoint | **Rebuild** | PR3.3 | Context assembly from Booski's own records. |
| `detect-gaps.sh` | Spots fresh projects and missing docs | **Rebuild** | PR3.8 | Command Centre suggestions from real data. |
| `pre-compact.sh` | Logs context compactions | **Ignore** | — | Claude Code mechanics. |
| `notify.sh` | Windows toast when Claude waits | **Ignore** | — | Booski's interface shows pending approvals. |
| `session-stop.sh` | Session log and a subagent spawn tally | **Rebuild** | PR3.2 | Booski records tokens and cost per request (D-P3-13), not only spawn counts. |
| `log-agent.sh`, `log-agent-stop.sh` | Audit trail of subagent starts and stops | **Rebuild** | PR3.4 | Agent runs recorded in PostgreSQL and the activity log. |
| `validate-skill-change.sh` | Suggests re-testing a changed skill | **Rebuild** | PR3.4 | Re-run agent evaluations when an agent configuration changes. |
| `log-instructions.sh` | Optional log of which instruction files loaded | **Ignore** | — | Diagnostic only. |
| `update-check.sh` | Checks for CCGS updates | **Ignore** | — | Not applicable. |
| `yaml-helper.sh` | Configuration helper library | **Ignore** | — | Booski stores settings in PostgreSQL. |

**Permission policy in `settings.json`:**

| Item | Class | Phase | Reason |
|---|---|---|---|
| Ask-first default permission mode | **Adapt** | PR3.5 | Equivalent to Booski's "Execute with approval" default. |
| Deny list: recursive deletes, force-push, `git reset --hard`, `git clean -f`, `sudo`, `chmod 777`, reading or writing `.env` files, editing Unreal binaries | **Adapt** | PR3.5, PR3.7 | A good starting list for Booski's never-allowed operations, for both Bash and PowerShell. Booski should enforce it in the Local Worker, not only in Claude Code settings. |
| Allow list of CCGS helper scripts | **Ignore** | — | Specific to CCGS scripts. |

### 5.8 Rules

CCGS's rules reference makes two points worth carrying over:
- **Rules are guidance, not enforcement.** A path-scoped rule only loads when Claude *reads* a matching file, not when it creates one. Anything that must always hold belongs in enforcement.
- **A rule and an agent must never contradict each other.**

| Rule | Scope | Class | Phase | Reason |
|---|---|---|---|---|
| `gameplay-code.md` | Gameplay code (Unity: `Assets/**/Gameplay/**/*.cs`) | **Adapt** | 4 / PR3.7 | Data-driven values, delta time, no UI references. Good Unity coding guidance. |
| `engine-code.md` | Core code | **Adapt** | 4 / PR3.7 | No allocations in hot paths, thread safety. |
| `ai-code.md` | AI code | **Adapt** | 4 / PR3.7 | Budgets, debuggability, data-driven parameters. |
| `network-code.md` | Networking code | **Ignore (not now)** | — | Revisit for multiplayer. |
| `ui-code.md` | UI code | **Adapt** | 4 / PR3.7 | UI never owns game state; localisation-ready; accessible. |
| `design-docs.md` | `design/gdd/**` | **Adapt** | 5 | Required design-document sections; becomes Booski template structure. |
| `narrative.md` | Narrative docs | **Adapt** | 5 | Canon levels and voice consistency. |
| `data-files.md` | Data JSON | **Adapt** | 4 | JSON validity and naming. |
| `test-standards.md` | Tests (Unity: `Assets/Tests/**/*.cs`) | **Adapt** | 4 / PR3.7 | Test naming, coverage, fixtures. |
| `prototype-code.md` | Prototypes | **Adapt** | 5 | Relaxed standards with a documented hypothesis. |
| `shader-code.md` | Shaders | **Adapt** | 5 | Naming, performance, cross-platform. |
| `scene-files.md` | Unity `.unity`, `.prefab`, `.asset` files | **Adapt (priority)** | PR3.7 | Never hand-edit scene or asset YAML while the Unity Editor may have it open; never invent GUIDs or touch `.meta` files. Essential for safe Claude Code work on Unity repositories. |
| `agent-memory.md` | Agent memory | **Adapt** | PR3.3 | "A temporary absence must never be recorded as a durable fact" is a good memory-quality rule. |
| `skill-authoring.md` | Skills and agents | **Adapt** | PR3.4, PR3.5 | "A check must be able to report that it did not run." Booski's tools and reviews should always distinguish *not run* from *ran and found nothing*. |

### 5.9 Templates

| Group | Templates (CCGS file names, without `.md`) | Class | Phase | Booski home |
|---|---|---|---|---|
| Concept and design | `game-concept`, `game-brief`, `game-pillars`, `pitch-document`, `game-design-document`, `systems-index`, `level-design-document`, `economy-model`, `faction-design`, `narrative-character-sheet`, `player-journey`, `difficulty-curve`, `hud-design`, `ux-spec`, `interaction-pattern-library`, `accessibility-requirements`, `art-bible`, `sound-bible`, `quick-design-change`, `quick-design-new-system`, `quick-design-tuning`, `concept-doc-from-prototype`, `design-doc-from-implementation` | **Adapt** | 5 | Booski `template` documents (the knowledge module already supports the `template` kind). Section structure informs ours; wording rewritten. |
| Technical | `architecture-decision-record`, `technical-design-document`, `architecture-traceability`, `architecture-doc-from-code` | **Adapt** | 4 | ADRs map onto Booski **decisions**; the others become `template` documents. |
| Production | `sprint-plan`, `sprint-status` (YAML), `milestone-definition`, `story`, `risk-register-entry`, `project-stage-report`, `post-mortem`, `incident-response`, `session-state`, `start-paths`, `adoption-plan`, `adoption-summary` | **Adapt** (except `session-state`, `start-paths`, `adoption-*`: **Ignore**) | 4 | Booski milestones, tasks and reports. |
| Quality | `test-plan`, `test-evidence`, `bug-report`, `bug-closure-record`, `soak-test-protocol`, `vertical-slice-report`, `prototype-report` | **Adapt** | 4 | Quality & Oversight templates. |
| Release | `release-checklist-template`, `launch-checklist`, `release-notes`, `release-platform-requirements`, `patch-notes-brief`, `patch-notes-commentary`, `changelog-template`, `changelog-internal`, `certification-steam`, `certification-itch`, `certification-console`, `certification-none`, `certification-unknown` | **Adapt** | 6 | Studio Operations. Steam first, matching D-P3-8. |
| Framework | `SKILL-CONTRACT-TEMPLATE`, `help-escalation`, `help-where-you-are`, `help-where-you-are-minimal`, `guidance/`, `one-shot-lean/` | **Ignore** | — | CCGS framework internals and browser one-shot material. |

### 5.10 Documentation conventions

| Convention | Class | Phase | Reason |
|---|---|---|---|
| A root `CLAUDE.md` importing focused docs, plus `CLAUDE.md` files per folder (`design/`, `docs/`, `src/`, `studio-tests/`) | **Adapt** | PR3.7 | Booski already uses a root `CLAUDE.md` (PR3.0). Per-folder instructions are a good pattern for the guidance Booski places into game repositories. |
| ADRs with an accepted status, and registries (entities, technical requirements) | **Adapt** | 4 | ADRs → Booski decisions. Registries → structured records rather than YAML files. |
| One configuration file (`project.yaml`) with local overrides | **Rebuild** | PR3.2 | Booski keeps workspace and project settings in PostgreSQL. |
| A session checkpoint file (`production/session-state/active.md`) as "the memory, not the conversation" | **Rebuild** | PR3.3 | Same principle as Booski's "the repository is the source of truth" (D-P3-1), implemented as Booski memory. |
| "Helpers emit observations, never verdicts" | **Adapt** | PR3.5 | A good design rule for tools: tools report facts; reviewers and humans judge. |

### 5.11 Other material

| Item | Class | Phase | Reason |
|---|---|---|---|
| **Model tiers** (cheap model for read-only lookups, mid-tier for most work, top tier for multi-document synthesis and high-stakes verdicts; written as aliases, not model IDs) | **Adapt** | PR3.2 | Matches D-P3-13 (cheaper models for routine work). Booski's model routing should use the same task-based tiering, provider-agnostic (D-P3-4). |
| **Studio tests** (behavioural specs for each skill and agent, a catalogue, a quality rubric) | **Rebuild** | PR3.4 | Booski needs agent evaluation; the structure (spec + rubric + catalogue) is a good model. |
| **Engine reference docs** (version-pinned notes on deprecated APIs, breaking changes and best practice, with "last verified" dates) | **Rebuild** | 4 | The idea, a version-pinned engine reference that agents must check before using an API, is valuable. The content is CCGS's summary of vendor documentation (mostly `docs.unity3d.com`), goes stale, and carries third-party sourcing questions. Booski should build its own from the studio's pinned Unity version. |
| **Engine table** (`engines.tsv`: code, test and asset roots; run, build, test and smoke commands) | **Adapt** | 4 | A good shape for a per-project engine profile. Unity's row has **no** run, build, test or smoke commands in CCGS, so Booski must define them. |
| **Genre data** (74 files) | **Ignore (not now)** | 5 | Possibly useful for Concept Lab ideation; revisit in Phase 5. |
| **Browser "make me a game" route** (`/prototype`) | **Adapt (concepts only)** | 5 | Concepts worth borrowing: one round of questions with sensible defaults; a one-page brief that keeps the human's own words; automated checks before hand-over; an honest hand-over that marks each brief item built, missing, broken or not assessed, and says "Not yet played by a person". The browser-game build itself is ignored. |
| **Agent teams** (experimental multi-session) | **Ignore** | — | Claude Code specific; Booski orchestration replaces it. |
| Status line, upgrade guide, issue templates, funding links | **Ignore** | — | Repository-specific. |

## 6. Unity in depth

**Material reviewed:**
- `unity-specialist`, read in full;
- the structure of the four Unity sub-specialists;
- the Unity row of the engine table;
- the Unity engine reference, `VERSION.md` and its index;
- the Unity-scoped rules;
- Unity mentions in skills (30 skills mention Unity).

**Strengths (adapt):**
- **Concrete, opinionated Unity guidance in `unity-specialist`:**
  - composition over deep inheritance, and ScriptableObjects for data;
  - assembly definitions;
  - no `Find`, `FindObjectOfType` or `SendMessage` in production code;
  - cached component references and no allocations in hot paths;
  - Addressables instead of `Resources.Load`;
  - the new Input System;
  - UI Toolkit for runtime UI where possible;
  - a scriptable render pipeline (URP or HDRP);
  - a list of common pitfalls.

  This is directly useful as Game Development guidance and as Claude Code instructions for Unity repositories.
- **Clear delegation:** the lead delegates DOTS, shaders, Addressables and UI to four sub-specialists and escalates package and version decisions to the technical director.
- **Version awareness:** the agent must check a pinned version file, deprecated APIs and breaking changes before suggesting API code, and must mark anything not found there as **unverified**. Booski should keep this behaviour.
- **Safe scene and asset handling:** never hand-edit `.unity`, `.prefab` or `.asset` YAML while an Editor may hold the file; never invent GUIDs; never touch `.meta` files. This is the most important single rule for Claude Code working in Unity repositories (PR3.7).

**Gaps (rebuild or define in Phase 4):**
- **No Unity commands:** the engine table has no Unity run, build, test or smoke commands. Booski will need Unity batch-mode build and Test Framework commands, run through the Local Worker.
- **Licensing in CI:** `test-setup` notes that Unity CI needs a `UNITY_LICENSE` secret. That is a secrets-handling question for PR3.5–PR3.7 and Phase 4.
- **The reference ages:** the Unity reference pins Unity 6.3 LTS; most of it was last verified 13 February 2026 (release information on 17 October 2026). The studio's real Unity version must be confirmed before anything is relied on.
- **Unproven:** CCGS's README says the engine routes are built but "not yet shown" in testing.

## 7. The two routes: assessment and recommendation

As agreed when PR3.1 was approved, the audit assesses both routes and recommends one. **The human decides.**

| | **Route A: Booski agent configurations** (PR3.4) | **Route B: curated `.claude/` toolkit in game repositories** (PR3.7) |
|---|---|---|
| What it means | CCGS's roles, responsibilities, delegation maps, gates and workflows are rewritten as Booski agent definitions and workflows, run by Booski's orchestrator. | A selected and edited copy of CCGS's agents, skills, rules and hooks is installed into each game repository, for Claude Code sessions started by the Local Worker. |
| Fit with agreed principles | Agents as configurations on shared orchestration (D-P3-3); provider-agnostic (D-P3-4); permission-aware memory (D-P3-5); approvals enforced and audited server-side (D-P3-6). | Tied to one tool (Claude Code); governance runs inside the session, mostly as prompt text and warn-only hooks. Booski's records wouldn't see decisions made inside the session. |
| Effort | Higher: content must be rewritten, not copied. Most mechanisms are rebuilt anyway in PR3.4–PR3.5. | Lower at first: the material is already in Claude Code format. |
| When it can start | PR3.4 | Only after PR3.6 (Local Worker) and PR3.7 |
| Maintenance | Booski owns its definitions; CCGS updates are reviewed and pulled in deliberately. | Six CCGS releases in seven weeks, and its docs reference specific Claude Code versions. A fork would need regular merging. |
| Licensing | Mostly new text inspired by CCGS; attribution only where substantial text is reused. | Substantial copying: MIT notice required in every repository. |
| Covers non-code departments | Yes (Concept Lab, Marketing, Operations, Post-Launch work happens in Booski). | Only work done inside a code repository. |
| Unity coding guidance | Available to Booski agents. | Available directly to Claude Code in the repository. |

**Recommendation (proposal):**

1. **Choose Route A as the toolkit's target.** It is the only route consistent with Booski's agreed architecture (agents as configurations, server-side enforcement, audit, provider independence), and it covers every department, not just code.
2. **Treat Route B as a derived output of Route A, delivered in PR3.7.** Booski would generate a small `.claude/` guidance pack for each game repository: `CLAUDE.md`, the Unity rules (especially `scene-files`), and the deny list. It would be produced from Booski's own definitions, with attribution where CCGS text is reused, rather than installing CCGS's toolkit.
3. **Don't import CCGS wholesale under either route** (D-P3-10).

**Why not Route B first:** it would be faster to try, but it would put the workforce's logic, approvals and history outside Booski, which is the opposite of the Control Plane's purpose. It also can't start before PR3.6–PR3.7.

## 8. Licence obligations

- **Licence:** MIT. The notice to keep is "Copyright (c) 2026 Donchitos", plus the MIT permission text.
- **The condition:** the copyright and permission notice must be included in "all copies or substantial portions of the Software".
- **Proposed practice for Booski (needs approval when the first reuse is proposed):**
  1. **Ideas, structure and patterns** (tiers, gate vocabularies, stage lists) are rewritten in Booski's own words. That is not copying text, but Booski should still credit CCGS as an inspiration in an acknowledgements note.
  2. **Any substantial text reused or adapted** (for example, parts of the Unity guidance or a template's wording) is recorded in a `THIRD_PARTY_NOTICES.md` with the full MIT text, the source path and the pinned commit, and the reused file is marked with its origin.
  3. **Where Booski places files into a game repository** (Route B output), any CCGS-derived file carries the notice in that repository too.
  4. **Don't reuse the Unity engine reference content:** it summarises third-party vendor documentation, so its sourcing is a separate question from CCGS's MIT licence.
- **Note on Booski's own wording:** Booski's agreed principle uses the same phrase as CCGS, "Question → Options → Decision → Draft → Approval". It is a short phrase describing a method, but crediting CCGS in an acknowledgements note would be good practice (see the proposal above).
- This is a practical summary, not legal advice.

## 9. Risks and open questions

**Risks:**
- **Pace of change:** CCGS changes fast. The audit is pinned to `abc0de7`; any later reuse should diff against a new pin and re-check.
- **Coupling to Claude Code versions:** CCGS documents behaviour of specific Claude Code versions (for example, how model pins apply in different modes). That kind of coupling is a reason not to depend on its mechanisms.
- **Unverified engine claims:** CCGS's own testing covers the browser route; the Unity route isn't proven.
- **Approval semantics:** CCGS lets AI directors approve stages, and lets orchestrated subagents write named files without a separate prompt. Booski must decide explicitly what an AI review may do on its own; by default it is advisory (D-P3-6).

**Open questions for the human** (answers recorded after review, 14 November 2026):
1. Route A or Route B (§7)? **Answered: Route A (D27).**
2. Should Booski add an acknowledgements note crediting CCGS now, or when the first CCGS-inspired item is built? **Answered: when the features are built (D28).**
3. Which Unity version does the studio use? This decides how any Unity reference is pinned (Phase 4). **Answered: Unity 6.3 LTS, with an upgrade expected later (D29).**
4. Should CCGS's finer production stages change Booski's project statuses? That would be a schema change in a later milestone.

---

## Appendix A: Skill-by-skill classification

| Skill | Family | Class | Phase | Booski home or note |
|---|---|---|---|---|
| `adopt` | Onboarding | Ignore | — | Brownfield audit of CCGS artefacts. |
| `architecture-decision` | Architecture | Adapt | 4 | Booski decisions (ADR form). |
| `architecture-review` | Architecture | Adapt | 4 | Traceability from design to decisions; verdicts include NOT ASSESSED. |
| `art-bible` | Concept and design | Adapt | 5 | Asset Production template and workflow. |
| `asset-audit` | Quality | Adapt | 5 | Asset naming and budget checks. |
| `asset-spec` | Concept and design | Adapt | 5 | Per-asset specs; AI generation prompts need their own policy. |
| `balance-check` | Quality | Adapt | 5 | Concept Lab and Q&O. |
| `brainstorm` | Concept and design | Adapt | 5 | Concept Lab ideation. |
| `bug-report` | Quality | Adapt | 4 | Booski tasks; drafts only, nothing filed upstream. |
| `bug-triage` | Quality | Adapt | 4 | Priority versus severity over Booski tasks. |
| `changelog` | Release | Ignore | — | Alias of `write-changelog`. |
| `code-review` | Quality | Adapt | 4 / PR3.7 | Pairs with PR3.7 diff review and `LP-CODE-REVIEW`. |
| `consistency-check` | Concept and design | Adapt | 5 | Cross-document conflicts. |
| `content-audit` | Planning | Adapt | 4 | Planned versus built. |
| `create-architecture` | Architecture | Adapt | 4 | Technical design document for a Unity project. |
| `create-control-manifest` | Architecture | Adapt | 4 / PR3.7 | Per-system must-do and never-do rules; input for repository instructions. |
| `create-epics` | Planning | Adapt | 4 | Milestones from design and architecture. |
| `create-stories` | Planning | Adapt | 4 | Tasks with acceptance criteria. |
| `cut` | Planning | Adapt | 4 | Scope cuts and a polish list; the human picks each cut. |
| `day-one-patch` | Release | Adapt | 6 | Launch patch workflow. |
| `design-review` | Concept and design | Adapt | 5 | Review of one design document. |
| `design-system` | Concept and design | Adapt | 5 | Section-by-section design authoring. |
| `dev-story` | Planning | Adapt | 4 / PR3.7 | Implement one task with tests through Claude Code. |
| `estimate` | Planning | Adapt | 4 | Effort estimates with confidence levels. |
| `gate-check` | Planning | Adapt | 4 | Stage-transition review feeding a human approval. |
| `help` | Onboarding | Ignore | — | Alias of `next-step`. |
| `hotfix` | Release | Adapt | 6 | Emergency fix with approvals and audit trail. |
| `launch-checklist` | Release | Adapt | 6 | Cross-department go/no-go. |
| `localize` | Release | Ignore (not now) | — | Revisit with `localization-lead`. |
| `map-systems` | Concept and design | Adapt | 5 | Systems decomposition and design order. |
| `milestone-review` | Planning | Adapt | 4 | Milestone progress and risk. |
| `next-step` | Onboarding | Adapt (idea) | PR3.8 | "The one next step" from real data in the Command Centre. |
| `onboard` | Onboarding | Ignore | — | Booski's interface and docs cover it. |
| `patch-notes` | Release | Adapt | 6–7 | Player-facing notes; Marketing Studio. |
| `perf-profile` | Quality | Adapt | 4 | Unity profiling against budgets. |
| `playtest-report` | Quality | Adapt | 5 | Structured playtest feedback. |
| `project-settings` | Onboarding | Ignore | — | Booski settings live in PostgreSQL. |
| `project-stage-detect` | Onboarding | Adapt (idea) | PR3.8 | Stage detection from Booski data. |
| `propagate-design-change` | Concept and design | Adapt | 5 | Find decisions made stale by a design change. |
| `prototype` | Concept and design | Adapt (concepts) | 5 | See [§5.11](#511-other-material); browser build ignored. |
| `qa-plan` | Quality | Adapt | 4 | Test plan per milestone. |
| `quick-design` | Concept and design | Adapt | 5 | Lightweight change specs. |
| `regression-suite` | Quality | Adapt | 4 | Regression coverage of critical paths. |
| `release-checklist` | Release | Adapt | 6 | Pre-release checks; Steam certification first. |
| `retrospective` | Planning | Adapt | 4 | Milestone retrospectives. |
| `reverse-document` | Concept and design | Adapt | 4 | Documents for existing Unity projects. |
| `review-all-gdds` | Concept and design | Adapt | 5 | Holistic design review (top model tier). |
| `scope-check` | Planning | Adapt | 4 | Scope creep against the plan. |
| `security-audit` | Quality | Ignore (not now) | — | Revisit with `security-engineer`. |
| `settings` | Onboarding | Ignore | — | Alias of `project-settings`. |
| `setup-engine` | Onboarding | Ignore | — | Replaced by a Booski project engine profile (Phase 4). |
| `skill-improve` | Framework | Rebuild | PR3.4 | Agent evaluation loop. |
| `skill-test` | Framework | Rebuild | PR3.4 | Agent evaluation specs and rubric. |
| `smoke-check` | Quality | Adapt | 4 | Needs Unity commands (see [§6](#6-unity-in-depth)). |
| `soak-test` | Quality | Adapt | 5 | Extended-play protocol. |
| `sprint-plan` | Planning | Adapt | 4 | Milestone planning. |
| `sprint-status` | Planning | Adapt | 4 | Status snapshot (cheapest model tier). |
| `start` | Onboarding | Ignore | — | Booski onboarding replaces it. |
| `story-done` | Planning | Adapt | 4 / PR3.7 | Verify each acceptance criterion before closing a task. |
| `story-readiness` | Planning | Adapt | 4 | Is a task ready to implement? |
| `team-audio` | Team orchestration | Rebuild | PR3.4 → 5 | Team workflow pattern. |
| `team-combat` | Team orchestration | Rebuild | PR3.4 → 4–5 | Team workflow pattern. |
| `team-level` | Team orchestration | Rebuild | PR3.4 → 5 | Team workflow pattern. |
| `team-live-ops` | Team orchestration | Rebuild | PR3.4 → 7 | Team workflow pattern. |
| `team-narrative` | Team orchestration | Rebuild | PR3.4 → 5 | Team workflow pattern. |
| `team-polish` | Team orchestration | Rebuild | PR3.4 → 4 | Team workflow pattern. |
| `team-qa` | Team orchestration | Rebuild | PR3.4 → 4 | Team workflow pattern. |
| `team-release` | Team orchestration | Rebuild | PR3.4 → 6 | Team workflow pattern. |
| `team-ui` | Team orchestration | Rebuild | PR3.4 → 4–5 | Team workflow pattern. |
| `tech-debt` | Quality | Adapt | 4 | Technical-debt register as Booski records. |
| `test-evidence-review` | Quality | Adapt | 4 | ADEQUATE / INCOMPLETE / MISSING / NOT ASSESSED per task. |
| `test-flakiness` | Quality | Adapt | 4 | Flaky tests from CI history. |
| `test-helpers` | Quality | Adapt | 4 | Unity test helpers. |
| `test-setup` | Quality | Adapt | 4 | Unity Test Framework and CI; `UNITY_LICENSE` handling. |
| `ux-design` | Concept and design | Adapt | 5 | UX specs. |
| `ux-review` | Concept and design | Adapt | 5 | UX review verdicts. |
| `vertical-slice` | Planning | Adapt | 4–5 | Pre-production validation. |
| `write-changelog` | Release | Adapt | 6 | Changelogs from Git and milestones. |

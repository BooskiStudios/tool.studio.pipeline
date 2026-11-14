# Booski Studios — Product Vision

> **What this document is:** the agreed long-term vision for Booski Studios: what we are building and why.
> It describes intent, not current state. What actually exists today is in [CURRENT_STATUS.md](CURRENT_STATUS.md);
> how and when we get there is in [ROADMAP.md](ROADMAP.md); how it is built is in [ARCHITECTURE.md](ARCHITECTURE.md).
>
> Source: the PR3.0 brief (agreed 14 November 2026). Change this document only when the vision itself changes,
> and record the change in [DECISIONS.md](DECISIONS.md).

## 1. What Booski is

Booski Studios is an **AI-powered operating system for an independent game development studio**.

It starts by supporting a solo developer working on a small number of projects. The architecture must also accommodate a growing team, multiple games and, potentially, multiple studios.

The central idea is to bring the **entire lifecycle of independent game development into one coordinated environment**, where AI is an active part of the studio's workflow. It should not be something we open in another browser tab when we need help. Booski acts as the **central coordinator**, connecting specialist agents, knowledge, tools, workflows and development environments.

Booski should help us:

- discover and develop game ideas;
- design gameplay systems and worlds;
- plan and manage game development;
- build games using AI-assisted development workflows;
- create and manage game assets;
- test, debug and improve projects;
- produce marketing and promotional content;
- manage studio operations;
- understand player feedback after release;
- learn from previous projects to improve future ones.

## 2. The studio lifecycle

**DISCOVER → CREATE → LAUNCH → LEARN → IMPROVE**

The stages feed into one another. For example, lessons learned from a released game should inform future game concepts, development decisions, asset pipelines and production workflows.

## 3. The departments

The departments are the studio's functional areas. They all share the same underlying AI infrastructure, knowledge systems, permissions and orchestration. They are not separate products.

> The department names below match the seven departments Booski Core seeds into every workspace (see [ARCHITECTURE.md](ARCHITECTURE.md#4-control-plane-partially-built)).
> **Booski AI Core** and **Cross-Project Studio Intelligence** are platform capabilities, not workspace departments.

### 3.1 Booski AI Core (platform)

The central intelligence and orchestration layer that makes every other department intelligent and connected.

- AI provider integrations; a model registry and model selection; a provider-agnostic architecture.
- Model routing based on task complexity, capability and cost.
- Persistent workspace and project memory; shared knowledge and contextual retrieval.
- Agent definitions, orchestration and multi-agent delegation.
- Task execution and progress reporting.
- Tool registration and controlled execution.
- Usage, token and cost tracking.
- Logging, retries and error recovery.
- Human approvals and oversight.
- Cross-project knowledge and learning.

**Anthropic is the initial AI provider.** Other providers, including OpenAI, must be addable without rebuilding the core platform.

### 3.2 Concept Lab

Where game ideas become properly developed concepts and projects.

- Brainstorming and ideation; genre and audience research; competitor and market research.
- Gameplay concepts, core loops, mechanics and systems design.
- Worldbuilding, narrative, characters, factions and lore.
- Game Design Documents.
- Technical feasibility assessments, scope and production estimates, prototype planning.
- Design reviews and consistency checks.

Over time Concept Lab should understand our previous projects, reusable mechanics and studio capabilities, so its recommendations become better informed.

### 3.3 Game Development

Where games are actually built. **Unity and C# come first**; Unreal Engine support is considered later.

- Understand existing game projects and codebases; inspect scripts, scenes and prefabs.
- Help with software architecture.
- Create and modify authorised project files; implement gameplay systems.
- Debug errors, run automated tests, build projects and verify build results.
- Track technical debt.
- Coordinate programming, technical design and QA agents.

The intention is for Booski to coordinate substantial development tasks through Claude Code and other authorised execution tools.

### 3.4 Asset Production

A **shared** production capability for game and marketing assets. It is not a separate system per game.

- Asset briefs and specifications; generation and refinement.
- Organisation and cataloguing; art direction and consistency; validation.
- Reusable asset libraries.
- Integration with game projects and marketing workflows.

### 3.5 Marketing Studio

Promoting our games and building an audience.

- Devlog planning and production; trailer production workflows.
- Social media content; scripts, captions and descriptions; promotional graphics.
- Turning development notes and gameplay footage into promotional material.
- Supporting our own voice recordings and audio clean-up.
- Content calendars and publishing workflows.

**Publishing actions require human approval.**

### 3.6 Studio Operations

The operational management layer: project management, roadmaps and milestones, tasks and workstreams, documentation, budget tracking, performance reporting, release planning, team coordination and studio-wide reporting.

It connects directly to the existing Booski project, task, approval and documentation infrastructure.

### 3.7 Quality & Oversight

Quality, security and governance across **all** departments, not isolated in one workspace.

- Testing, QA, code reviews and design reviews.
- Security checks and permission enforcement.
- Approval gates and audit trails.
- Source-control oversight.
- AI spending limits.
- Human review of significant decisions and actions.

### 3.8 Post-Launch Intelligence

A longer-term system for understanding how our games perform and what players think.

- **Sources:** Steam reviews first, then Discord and YouTube comments. Game telemetry where available and authorised.
- Classify bugs, UX problems, balance concerns, feature requests and positive feedback; identify duplicates.
- Assess frequency, severity, confidence and potential impact.
- Preserve source links and evidence, and **distinguish actual player statements from AI interpretations**.
- Recommend priorities; convert *approved* issues into development tasks; monitor whether issues recur after patches.

### 3.9 Cross-Project Studio Intelligence (platform, long term)

Booski learns from everything the studio creates:

- identifies reusable systems, successful development patterns and recurring technical problems;
- reuses proven workflows and shares lessons between projects;
- feeds knowledge into Concept Lab and spots opportunities for new games.

This is a long-term capability. It must not add unnecessary complexity to earlier phases.

## 4. The AI workforce philosophy

Booski has specialist AI capabilities across its departments, but **specialists are not separate, independent AI systems**. Agents are **configurations** that run through shared orchestration infrastructure. Each agent eventually has:

- a defined role, with responsibilities and boundaries;
- instructions;
- permitted tools;
- knowledge requirements;
- a preferred model;
- quality criteria and escalation rules;
- an execution history.

### Levels of autonomy

1. **Assist:** AI advises, explains and proposes.
2. **Execute with approval:** AI prepares work and waits for approval.
3. **Controlled autonomy:** AI completes predefined low-risk tasks within strict permissions.
4. **Coordinated workflows:** several agents collaborate with human oversight and approval gates.

**The human remains the final decision-maker.**

### Collaborative design principle

**Question → Options → Decision → Draft → Approval**

AI should challenge assumptions, explain trade-offs and make recommendations. It must not silently make important creative, architectural or business decisions.

## 5. AI cost and efficiency principles

Efficient AI usage is a core requirement. **Not every task needs an AI agent.**

- Reuse existing skills, workflows and templates where appropriate.
- Avoid unnecessary agent delegation.
- Use lower-cost models for suitable routine work; escalate to more capable models only when justified.
- Use deterministic scripts and tools instead of AI where possible.
- Reuse project context rather than repeatedly sending enormous prompts; store structured, reusable knowledge.
- Avoid duplicate research; cache appropriate results.
- Track costs by workspace, project, agent, provider and task where practical.

## 6. Non-negotiables

- **The repository is the permanent source of truth.** Booski must be understandable from its documentation, not from past conversations.
- **Security is enforced by the backend**, not just the frontend. Project permissions may narrow workspace permissions but never widen them.
- **Significant actions are approved and auditable**: destructive operations, publishing, significant external actions, spending money, sensitive file operations, and source-control actions (commit, push, merge).
- **Secrets never go into source control.**
- **The existing interface is preserved**: it is connected to real functionality progressively, not redesigned unnecessarily.

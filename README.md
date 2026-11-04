# Booski Studios — Frontend Foundation v0.3

React + TypeScript + Vite responsive prototype.

## Run
Requires Node.js 20+:
```bash
npm install
npm run dev
```
Open the local URL shown by Vite (usually http://localhost:5173).

## v0.3 changes
- Project selection in the sidebar is highlighted only while inside that project's workspace.
- Project selector moved into the Home dashboard's Project Overview panel.
- Removed the decorative quote/crown hero copy; centred the AI command bar.
- Game Library is now a Steam-style project library.
- Research is a research-document library with a file picker UI.
- Templates is a reusable template bank with Preview and Use template actions.
- Reference Vault moved into individual project workspaces.
- Removed the New Project button from Studio Operations.
- Studio Operations now has a vertical management menu and interactive agent workflow canvas. Hover/focus an agent to inspect its demo workload.
- Department tabs have been redesigned per department; Work Queue now contains separate queued-work records rather than duplicating active workspace items.

## Prototype limitations
All records and metrics are demo content. The research file picker only selects a local file name; it does not upload or persist file bytes. The agent canvas is illustrative and does not represent live agent execution. The command bar is not connected to an AI model. Project, task and reference data are not yet stored in a backend.

## Next milestone
Build the FastAPI + SQLite core and replace demo state with persistent API-backed records.

## v0.5 — Studio Operations refinement

- Removed Budgets & Costs and Reports & Performance from Studio Operations; these are no longer duplicated in its management menu. Cost & Usage remains a dedicated Studio System.
- Studio Operations now focuses on Overview, Projects & Roadmaps, Tasks & Milestones, and Studio Calendar.
- The agent workflow canvas can be dragged to pan around the diagram.
- Agent nodes are no longer clickable; hovering or keyboard-focusing an agent reveals its current demo tasks. The task detail panel is hidden when no agent is being inspected.
- Agent activity remains illustrative and is not connected to live execution.

## v0.4 — Command Centre & studio systems

- Home is now the Booski Studio Command Centre, with studio-wide summary metrics, illustrative AI workforce, and items requiring approval.
- Added dedicated Agent Management and Cost & Usage pages beneath Templates in the Studio Systems sidebar group.
- Added a central Decision Log with department filtering, plus a Decision Log tab inside each department workspace.
- Added Approvals Centre, Integrations Hub, Studio Knowledge Base, and Activity & Audit pages.
- Added an explicit distinction between studio-wide knowledge and project-specific knowledge in the knowledge interface.
- All new operational records are illustrative demo content. There is no live agent execution, billing telemetry, integration connection, persistent approval handling, or audit backend yet.


## v0.7 updates
- Sidebar navigation, project links, knowledge links and studio systems now live inside a dedicated scrollable region; the profile control remains pinned at the bottom.
- Added Framer Motion page transitions, agent-node entrance animations and animated workflow paths.
- Agent workflow connectors use curved SVG Bezier paths with a soft glow and moving dash treatment to simulate orchestrator routing.
- Added Recharts visualisations to Cost & Usage using explicitly labelled illustrative sample data.
- Added `framer-motion` and `recharts` dependencies.

The charts and agent flows are visual prototypes, not connected to live usage or task execution.

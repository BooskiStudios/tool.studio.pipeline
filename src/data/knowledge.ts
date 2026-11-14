import type { KnowledgeDoc, ResearchDoc, Template } from "../types";

/** DEMO DATA — sample research documents. Nothing is stored or processed. */
export const demoResearchDocs: ResearchDoc[] = [
  { id: "res-1", title: "Indie Horror Market Landscape", detail: "Market research · 18 sources · 04 Nov 2026", format: "PDF" },
  { id: "res-2", title: "First-Person Horror Competitor Review", detail: "Competitor analysis · 12 games · 02 Nov 2026", format: "DOCX" },
  { id: "res-3", title: "Audience & Steam Tag Analysis", detail: "Audience research · 9 sources · 29 Oct 2026", format: "PDF" },
  { id: "res-4", title: "Survival Game Pricing Benchmarks", detail: "Pricing research · 15 sources · 26 Oct 2026", format: "XLSX" },
];

/** DEMO DATA — reusable studio document templates. */
export const demoTemplates: Template[] = [
  { id: "tpl-concept", name: "Game Concept Brief", description: "Structured starting point for a new game idea", category: "Concept" },
  { id: "tpl-market", name: "Market Research Report", description: "Competitor landscape, audience and opportunity", category: "Research" },
  { id: "tpl-gdd", name: "Game Design Document", description: "Core mechanics, systems, progression and experience", category: "Design" },
  { id: "tpl-asset", name: "Asset Production Brief", description: "Asset requirements, style and technical constraints", category: "Assets" },
  { id: "tpl-dev", name: "Development Task", description: "Implementation brief with acceptance criteria", category: "Development" },
  { id: "tpl-devlog", name: "Devlog Script", description: "Narrative structure for a development update", category: "Marketing" },
  { id: "tpl-qa", name: "QA Test Plan", description: "Test cases, expected results and evidence", category: "Quality" },
  { id: "tpl-feedback", name: "Post-Launch Feedback Report", description: "Evidence-backed player issue analysis", category: "Live Ops" },
];

/** DEMO DATA — Studio Knowledge Base documents. */
export const demoKnowledgeDocs: KnowledgeDoc[] = [
  { id: "kb-identity", title: "Studio Identity & Brand Guide", detail: "Studio-wide · Brand and communication standards", scope: "Studio-wide" },
  { id: "kb-principles", title: "AI Working Principles", detail: "Studio-wide · Approval boundaries and operating principles", scope: "Studio-wide" },
  { id: "kb-unity", title: "Unity Development Standards", detail: "Game Development · Coding and project conventions", scope: "Game Development" },
  { id: "kb-mournforge", title: "Mournforge Design Direction", detail: "Mournforge · World, tone and art direction", scope: "Concept Lab" },
  { id: "kb-marketing", title: "Marketing Voice & Style", detail: "Marketing Studio · Tone, formats and publishing guidelines", scope: "Marketing Studio" },
];

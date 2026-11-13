/** Every URL in the app, so links and routes cannot drift apart. */
export const paths = {
  home: "/",
  department: (slug: string) => `/departments/${slug}`,
  project: (slug: string) => `/projects/${slug}`,
  operations: "/operations",
  tasks: "/tasks",
  library: "/library",
  research: "/research",
  templates: "/templates",
  agents: "/agents",
  costUsage: "/cost-usage",
  decisions: "/decisions",
  approvals: "/approvals",
  integrations: "/integrations",
  knowledge: "/knowledge",
  activity: "/activity",
  settings: "/settings",
} as const;

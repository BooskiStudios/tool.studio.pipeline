/** Every URL in the app, so links and routes cannot drift apart. */
export const paths = {
  home: "/",
  login: "/login",
  join: "/join",
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

/** Links that open one record's detail panel on its list page (e.g. `/tasks?task=…`). */
export const recordLinks = {
  task: (id: string) => `${paths.tasks}?task=${encodeURIComponent(id)}`,
  document: (id: string) => `${paths.knowledge}?document=${encodeURIComponent(id)}`,
  decision: (id: string) => `${paths.decisions}?decision=${encodeURIComponent(id)}`,
  approval: (id: string) => `${paths.approvals}?approval=${encodeURIComponent(id)}`,
} as const;

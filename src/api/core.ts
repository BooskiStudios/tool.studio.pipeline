/** Typed calls for every Booski Core endpoint the app uses. Workspace data lives under `/w/{slug}`. */

import { apiRequest, type QueryValue } from "./client";
import type {
  ActivityEvent, Approval, ApprovalInput, AssignableRole, Comment, Decision, DecisionInput, Department,
  DocumentInput, DocumentSummary, Invitation, InvitationAccepted, InvitationCreated, InvitationPreview,
  LoginResponse, MeResponse, Member, Milestone, MilestoneInput, Page, Project, ProjectAccess, ProjectInput,
  ProjectMember, Readiness, Revision, RevisionSummary, ReviewAction, Review, SessionInfo, StudioDocument, Task,
  TaskInput, Workspace, Workstream,
} from "./types";

type Query = Record<string, QueryValue>;
const w = (slug: string) => `/w/${encodeURIComponent(slug)}`;
const id = (value: string) => encodeURIComponent(value);

export const auth = {
  me: (signal?: AbortSignal) => apiRequest<MeResponse>("/auth/me", { signal, expectUnauthenticated: true }),
  login: (email: string, password: string) =>
    apiRequest<LoginResponse>("/auth/login", { method: "POST", body: { email, password }, expectUnauthenticated: true }),
  logout: () => apiRequest<void>("/auth/logout", { method: "POST", expectUnauthenticated: true }),
  sessions: (signal?: AbortSignal) => apiRequest<SessionInfo[]>("/auth/sessions", { signal }),
  revokeSession: (sessionId: string) => apiRequest<void>(`/auth/sessions/${id(sessionId)}`, { method: "DELETE" }),
  revokeOtherSessions: () => apiRequest<{ revoked: number }>("/auth/sessions/revoke-others", { method: "POST" }),
  changePassword: (current_password: string, new_password: string) =>
    apiRequest<{ revoked: number }>("/auth/password", { method: "POST", body: { current_password, new_password } }),
};

export const health = {
  ready: (signal?: AbortSignal) => apiRequest<Readiness>("/health/ready", { signal }),
};

export const workspaces = {
  create: (name: string, slug: string) => apiRequest<Workspace>("/workspaces", { method: "POST", body: { name, slug } }),
  get: (ws: string, signal?: AbortSignal) => apiRequest<Workspace>(w(ws), { signal }),
  rename: (ws: string, name: string) => apiRequest<Workspace>(w(ws), { method: "PATCH", body: { name } }),
  members: (ws: string, signal?: AbortSignal) => apiRequest<Member[]>(`${w(ws)}/members`, { signal }),
  changeRole: (ws: string, userId: string, role: AssignableRole) =>
    apiRequest<Member>(`${w(ws)}/members/${id(userId)}`, { method: "PATCH", body: { role } }),
  removeMember: (ws: string, userId: string) => apiRequest<void>(`${w(ws)}/members/${id(userId)}`, { method: "DELETE" }),
  invitations: (ws: string, signal?: AbortSignal) => apiRequest<Invitation[]>(`${w(ws)}/invitations`, { signal }),
  invite: (ws: string, email: string, role: AssignableRole) =>
    apiRequest<InvitationCreated>(`${w(ws)}/invitations`, { method: "POST", body: { email, role } }),
  revokeInvitation: (ws: string, invitationId: string) =>
    apiRequest<void>(`${w(ws)}/invitations/${id(invitationId)}`, { method: "DELETE" }),
};

export const invitations = {
  preview: (token: string) =>
    apiRequest<InvitationPreview>("/invitations/preview", { method: "POST", body: { token }, expectUnauthenticated: true }),
  accept: (token: string, account?: { display_name: string; password: string }) =>
    apiRequest<InvitationAccepted>("/invitations/accept", {
      method: "POST",
      body: { token, ...account },
      expectUnauthenticated: true,
    }),
};

export const departments = {
  list: (ws: string, signal?: AbortSignal) => apiRequest<Department[]>(`${w(ws)}/departments`, { signal }),
};

export const projects = {
  list: (ws: string, query: Query, signal?: AbortSignal) =>
    apiRequest<Page<Project>>(`${w(ws)}/projects`, { query, signal }),
  get: (ws: string, slug: string, signal?: AbortSignal) => apiRequest<Project>(`${w(ws)}/projects/${id(slug)}`, { signal }),
  create: (ws: string, body: ProjectInput) => apiRequest<Project>(`${w(ws)}/projects`, { method: "POST", body }),
  update: (ws: string, slug: string, body: ProjectInput) =>
    apiRequest<Project>(`${w(ws)}/projects/${id(slug)}`, { method: "PATCH", body }),
  members: (ws: string, slug: string, signal?: AbortSignal) =>
    apiRequest<ProjectMember[]>(`${w(ws)}/projects/${id(slug)}/members`, { signal }),
  setMember: (ws: string, slug: string, userId: string, access: ProjectAccess) =>
    apiRequest<ProjectMember>(`${w(ws)}/projects/${id(slug)}/members/${id(userId)}`, { method: "PUT", body: { access } }),
  removeMember: (ws: string, slug: string, userId: string) =>
    apiRequest<void>(`${w(ws)}/projects/${id(slug)}/members/${id(userId)}`, { method: "DELETE" }),
  workstreams: (ws: string, slug: string, signal?: AbortSignal) =>
    apiRequest<Workstream[]>(`${w(ws)}/projects/${id(slug)}/workstreams`, { signal }),
  createWorkstream: (ws: string, slug: string, body: { department_id: string; name: string; description?: string }) =>
    apiRequest<Workstream>(`${w(ws)}/projects/${id(slug)}/workstreams`, { method: "POST", body }),
  milestones: (ws: string, slug: string, signal?: AbortSignal) =>
    apiRequest<Milestone[]>(`${w(ws)}/projects/${id(slug)}/milestones`, { signal }),
  createMilestone: (ws: string, slug: string, body: MilestoneInput) =>
    apiRequest<Milestone>(`${w(ws)}/projects/${id(slug)}/milestones`, { method: "POST", body }),
};

export const milestones = {
  update: (ws: string, milestoneId: string, body: MilestoneInput) =>
    apiRequest<Milestone>(`${w(ws)}/milestones/${id(milestoneId)}`, { method: "PATCH", body }),
};

export const tasks = {
  list: (ws: string, query: Query, signal?: AbortSignal) => apiRequest<Page<Task>>(`${w(ws)}/tasks`, { query, signal }),
  get: (ws: string, taskId: string, signal?: AbortSignal) => apiRequest<Task>(`${w(ws)}/tasks/${id(taskId)}`, { signal }),
  create: (ws: string, body: TaskInput) => apiRequest<Task>(`${w(ws)}/tasks`, { method: "POST", body }),
  update: (ws: string, taskId: string, body: TaskInput) =>
    apiRequest<Task>(`${w(ws)}/tasks/${id(taskId)}`, { method: "PATCH", body }),
  history: (ws: string, taskId: string, query: Query, signal?: AbortSignal) =>
    apiRequest<Page<ActivityEvent>>(`${w(ws)}/tasks/${id(taskId)}/history`, { query, signal }),
  comments: (ws: string, taskId: string, query: Query, signal?: AbortSignal) =>
    apiRequest<Page<Comment>>(`${w(ws)}/tasks/${id(taskId)}/comments`, { query, signal }),
  addComment: (ws: string, taskId: string, body: string) =>
    apiRequest<Comment>(`${w(ws)}/tasks/${id(taskId)}/comments`, { method: "POST", body: { body } }),
  editComment: (ws: string, commentId: string, body: string) =>
    apiRequest<Comment>(`${w(ws)}/comments/${id(commentId)}`, { method: "PATCH", body: { body } }),
  deleteComment: (ws: string, commentId: string) => apiRequest<void>(`${w(ws)}/comments/${id(commentId)}`, { method: "DELETE" }),
};

export const documents = {
  list: (ws: string, query: Query, signal?: AbortSignal) =>
    apiRequest<Page<DocumentSummary>>(`${w(ws)}/documents`, { query, signal }),
  get: (ws: string, documentId: string, signal?: AbortSignal) =>
    apiRequest<StudioDocument>(`${w(ws)}/documents/${id(documentId)}`, { signal }),
  create: (ws: string, body: DocumentInput) => apiRequest<StudioDocument>(`${w(ws)}/documents`, { method: "POST", body }),
  update: (ws: string, documentId: string, body: DocumentInput) =>
    apiRequest<StudioDocument>(`${w(ws)}/documents/${id(documentId)}`, { method: "PATCH", body }),
  revisions: (ws: string, documentId: string, signal?: AbortSignal) =>
    apiRequest<RevisionSummary[]>(`${w(ws)}/documents/${id(documentId)}/revisions`, { signal }),
  revision: (ws: string, documentId: string, revisionNo: number, signal?: AbortSignal) =>
    apiRequest<Revision>(`${w(ws)}/documents/${id(documentId)}/revisions/${revisionNo}`, { signal }),
};

export const decisions = {
  list: (ws: string, query: Query, signal?: AbortSignal) => apiRequest<Page<Decision>>(`${w(ws)}/decisions`, { query, signal }),
  get: (ws: string, decisionId: string, signal?: AbortSignal) =>
    apiRequest<Decision>(`${w(ws)}/decisions/${id(decisionId)}`, { signal }),
  create: (ws: string, body: DecisionInput) => apiRequest<Decision>(`${w(ws)}/decisions`, { method: "POST", body }),
  update: (ws: string, decisionId: string, body: DecisionInput) =>
    apiRequest<Decision>(`${w(ws)}/decisions/${id(decisionId)}`, { method: "PATCH", body }),
  history: (ws: string, decisionId: string, signal?: AbortSignal) =>
    apiRequest<Page<ActivityEvent>>(`${w(ws)}/decisions/${id(decisionId)}/history`, { query: { limit: 100 }, signal }),
};

export const approvals = {
  list: (ws: string, query: Query, signal?: AbortSignal) => apiRequest<Page<Approval>>(`${w(ws)}/approvals`, { query, signal }),
  get: (ws: string, approvalId: string, signal?: AbortSignal) =>
    apiRequest<Approval>(`${w(ws)}/approvals/${id(approvalId)}`, { signal }),
  create: (ws: string, body: ApprovalInput) => apiRequest<Approval>(`${w(ws)}/approvals`, { method: "POST", body }),
  reviews: (ws: string, approvalId: string, signal?: AbortSignal) =>
    apiRequest<Review[]>(`${w(ws)}/approvals/${id(approvalId)}/reviews`, { signal }),
  review: (ws: string, approvalId: string, action: ReviewAction, comment: string) =>
    apiRequest<Approval>(`${w(ws)}/approvals/${id(approvalId)}/reviews`, { method: "POST", body: { action, comment } }),
  resubmit: (ws: string, approvalId: string, comment: string) =>
    apiRequest<Approval>(`${w(ws)}/approvals/${id(approvalId)}/resubmit`, { method: "POST", body: { comment } }),
  cancel: (ws: string, approvalId: string, comment: string) =>
    apiRequest<Approval>(`${w(ws)}/approvals/${id(approvalId)}/cancel`, { method: "POST", body: { comment } }),
};

export const activity = {
  list: (ws: string, query: Query, signal?: AbortSignal) =>
    apiRequest<Page<ActivityEvent>>(`${w(ws)}/activity`, { query, signal }),
};

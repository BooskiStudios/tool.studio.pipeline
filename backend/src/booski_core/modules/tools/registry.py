"""The tool registry: every tool's name, kind, description, input schema and implementation."""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import select
from sqlalchemy.orm import Session

from booski_core.access.dependencies import WorkspaceContext
from booski_core.access.projects import get_project, project_capabilities
from booski_core.access.roles import Capability
from booski_core.core.errors import ProblemError
from booski_core.modules.ai.providers.base import ToolSpec
from booski_core.modules.decisions.schemas import DecisionCreate, DecisionOption
from booski_core.modules.decisions.service import get_decision
from booski_core.modules.departments.service import get_department
from booski_core.modules.knowledge.schemas import DocumentCreate
from booski_core.modules.knowledge.service import current_body, get_document
from booski_core.modules.memory.service import list_memories as memory_list
from booski_core.modules.milestones.models import Milestone
from booski_core.modules.milestones.service import list_milestones as milestone_list
from booski_core.modules.projects.models import Project
from booski_core.modules.projects.service import list_projects as project_list
from booski_core.modules.retrieval.search import search
from booski_core.modules.tasks.schemas import TaskCreate
from booski_core.modules.tasks.service import get_task as task_get
from booski_core.modules.tasks.service import list_tasks as task_list
from booski_core.vocab import DocumentKind, MemoryKind, SourceType, TaskPriority, TaskStatus, ToolKind

# Verbs no tool may perform. Tools are named for what they do, so none may start with these (tested).
FORBIDDEN_ACTIONS = (
    "delete", "remove", "archive", "edit", "update", "assign", "publish", "send", "commit", "push",
    "merge", "deploy", "pay", "spend", "run", "execute",
)  # fmt: skip
MAX_READ_CHARS = 12_000  # about 4,000 tokens (D59)
LIST_LIMIT = 50

Slug = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


@dataclass
class ToolContext:
    """Where a tool runs: the run starter's permissions and the run's project (if any)."""

    db: Session
    ctx: WorkspaceContext
    project: Project | None


@dataclass(frozen=True)
class Proposal:
    """A change a propose tool staged. ``payload`` is the validated request body; ``records`` is how many
    records applying it would create (counted against the agent's change limit)."""

    summary: str
    payload: dict[str, Any]
    records: int


@dataclass(frozen=True)
class Tool:
    name: str
    kind: ToolKind
    description: str
    args: type[ToolInput]
    handler: Callable[[ToolContext, Any], str | Proposal]
    capability: Capability | None = None  # what applying a proposal needs in its project

    def spec(self) -> ToolSpec:
        schema = self.args.model_json_schema()
        schema.pop("title", None)
        return ToolSpec(name=self.name, description=self.description, input_schema=schema)


def _clip(text: str, limit: int = MAX_READ_CHARS) -> str:
    return text if len(text) <= limit else text[:limit] + "\n[…shortened: the rest was not included]"


def _project(tc: ToolContext, slug: str | None) -> Project | None:
    """The named project (404 if the starter can't see it), else the run's own project."""
    return get_project(tc.db, tc.ctx, slug=slug) if slug else tc.project


def _require(tc: ToolContext, project: Project | None, capability: Capability, what: str) -> None:
    if capability not in project_capabilities(tc.db, tc.ctx, project):
        raise ProblemError(403, f"The person who started this run isn't allowed to {what} here.")


# ---------------------------------------------------------------- read tools


class SearchArgs(ToolInput):
    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    types: list[SourceType] | None = Field(
        default=None, description="memory, document, decision; default all."
    )
    project: Slug | None = Field(default=None, description="Project slug: its records plus studio-wide ones.")


def _search(tc: ToolContext, a: SearchArgs) -> str:
    hits = search(
        tc.db, tc.ctx, a.query, project=_project(tc, a.project), types=a.types, limit=10, match_any=True
    )
    if not hits:
        return "No matching memory, documents or decisions."
    return "\n".join(f"- [{h.type}] {h.title} (id {h.id}): {h.snippet}" for h in hits)


class IdArgs(ToolInput):
    id: uuid.UUID


def _get_document(tc: ToolContext, a: IdArgs) -> str:
    document = get_document(tc.db, tc.ctx, a.id)
    if document.archived_at is not None:
        raise ProblemError(404, "Document not found.")
    return _clip(
        f"# {document.title}\nKind: {document.kind} · revision {document.current_revision}\n"
        f"Summary: {document.summary or '(none)'}\n\n{current_body(tc.db, document)}"
    )


def _get_decision(tc: ToolContext, a: IdArgs) -> str:
    d = get_decision(tc.db, tc.ctx, a.id)
    options = "\n".join(f"- {o.get('title')}: {o.get('summary', '')}" for o in d.options) or "(none recorded)"
    return _clip(
        f"# {d.title}\nStatus: {d.status}\nContext: {d.context or '(none)'}\nOptions:\n{options}\n"
        f"Outcome: {d.outcome or '(none)'}\nRationale: {d.rationale or '(none)'}"
    )


class MemoryArgs(ToolInput):
    project: Slug | None = None
    kind: MemoryKind | None = None


def _list_memories(tc: ToolContext, a: MemoryArgs) -> str:
    rows, _ = memory_list(
        tc.db,
        tc.ctx,
        project=_project(tc, a.project) if a.project else None,
        department_id=None,
        kinds=[a.kind] if a.kind else None,
        include_archived=False,
        limit=LIST_LIMIT,
        cursor=None,
    )
    return _clip("\n".join(f"- ({m.kind}) {m.content}" for m in rows) or "No memory entries.")


class NoArgs(ToolInput):
    pass


def _list_projects(tc: ToolContext, a: NoArgs) -> str:
    rows, _ = project_list(
        tc.db, tc.ctx, status=None, archived=False, q=None, sort="name", limit=LIST_LIMIT, cursor=None
    )
    return "\n".join(f"- {p.slug}: {p.name} ({p.status})" for p in rows) or "No projects."


class ProjectArgs(ToolInput):
    project: Slug


def _list_milestones(tc: ToolContext, a: ProjectArgs) -> str:
    project = get_project(tc.db, tc.ctx, slug=a.project)
    rows = milestone_list(tc.db, project, include_archived=False)
    return (
        "\n".join(
            f"- {m.name} (id {m.id}, {m.status}, due {m.target_date or 'not set'})" for m in rows[:LIST_LIMIT]
        )
        or "No milestones."
    )


class TaskListArgs(ToolInput):
    project: Slug | None = None
    milestone_id: uuid.UUID | None = None
    status: list[TaskStatus] | None = None


def _list_tasks(tc: ToolContext, a: TaskListArgs) -> str:
    rows, _ = task_list(
        tc.db,
        tc.ctx,
        project=_project(tc, a.project) if a.project else None,
        department_id=None,
        workstream_id=None,
        milestone_id=a.milestone_id,
        status=list(a.status) if a.status else None,
        priority=None,
        assignee=None,
        parent=None,
        q=None,
        archived=False,
        due_before=None,
        sort="position",
        limit=LIST_LIMIT,
        cursor=None,
    )
    return _clip("\n".join(f"- {t.title} (id {t.id}, {t.status}, {t.priority})" for t in rows) or "No tasks.")


def _get_task(tc: ToolContext, a: IdArgs) -> str:
    t = task_get(tc.db, tc.ctx, a.id)
    return _clip(
        f"# {t.title}\nStatus: {t.status} · priority {t.priority}\n\n{t.description or '(no description)'}"
    )


# ---------------------------------------------------------------- propose tools


class DocumentArgs(ToolInput):
    kind: DocumentKind = Field(
        description="design_doc, note, report, guide, research, reference or template."
    )
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    summary: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] = ""
    body: Annotated[str, Field(max_length=100_000, description="Markdown.")] = ""
    project: Slug | None = Field(default=None, description="Project slug; default: the run's project.")
    department: Slug | None = None


def _create_document(tc: ToolContext, a: DocumentArgs) -> Proposal:
    project = _project(tc, a.project)
    _require(tc, project, Capability.DOCUMENTS_WRITE, "write documents")
    department = get_department(tc.db, tc.ctx, slug=a.department) if a.department else None
    body = DocumentCreate(
        kind=a.kind,
        title=a.title,
        summary=a.summary,
        body=a.body,
        project_id=project.id if project else None,
        department_id=department.id if department else None,
    )
    return Proposal(f"Create {a.kind.replace('_', ' ')}: {a.title}"[:300], body.model_dump(mode="json"), 1)


class NewTask(ToolInput):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    description: Annotated[str, Field(max_length=20_000)] = ""
    priority: TaskPriority = "medium"


class TasksArgs(ToolInput):
    project: Slug | None = Field(default=None, description="Project slug; default: the run's project.")
    milestone_id: uuid.UUID | None = None
    tasks: list[NewTask] = Field(min_length=1, max_length=20)


def _create_tasks(tc: ToolContext, a: TasksArgs) -> Proposal:
    project = _project(tc, a.project)
    if project is None:
        raise ProblemError(422, "Say which project the tasks belong to.")
    _require(tc, project, Capability.TASKS_CREATE, "create tasks")
    if a.milestone_id is not None:
        milestone = tc.db.scalar(
            select(Milestone).where(Milestone.id == a.milestone_id, Milestone.project_id == project.id)
        )
        if milestone is None:
            raise ProblemError(404, "That milestone isn't in this project.")
    bodies = [
        TaskCreate(
            title=t.title,
            description=t.description,
            priority=t.priority,
            project_id=project.id,
            milestone_id=a.milestone_id,
        ).model_dump(mode="json")
        for t in a.tasks
    ]
    return Proposal(f"Create {len(bodies)} task(s) in {project.name}"[:300], {"tasks": bodies}, len(bodies))


class DecisionArgs(ToolInput):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    context: Annotated[str, Field(max_length=20_000)] = ""
    options: list[DecisionOption] = Field(default_factory=list, max_length=20)
    outcome: Annotated[str, Field(max_length=5_000)] = Field(
        default="", description="The recommended option."
    )
    rationale: Annotated[str, Field(max_length=20_000)] = ""
    project: Slug | None = Field(default=None, description="Project slug; default: the run's project.")


def _propose_decision(tc: ToolContext, a: DecisionArgs) -> Proposal:
    project = _project(tc, a.project)
    _require(tc, project, Capability.DECISIONS_WRITE, "record decisions")
    body = DecisionCreate(
        title=a.title,
        context=a.context,
        options=a.options,
        outcome=a.outcome,
        rationale=a.rationale,
        status="proposed",  # a person accepts it in the Decision Log
        project_id=project.id if project else None,
    )
    return Proposal(f"Propose decision: {a.title}"[:300], body.model_dump(mode="json"), 1)


TOOLS: dict[str, Tool] = {
    t.name: t
    for t in (
        Tool(
            "search_knowledge",
            "read",
            "Search memory, knowledge documents and decisions you can see.",
            SearchArgs,
            _search,
        ),
        Tool(
            "get_document",
            "read",
            "Read a knowledge document's current revision by id.",
            IdArgs,
            _get_document,
        ),
        Tool("get_decision", "read", "Read a decision from the Decision Log by id.", IdArgs, _get_decision),
        Tool(
            "list_memories",
            "read",
            "List memory entries (facts, conventions, lessons, preferences).",
            MemoryArgs,
            _list_memories,
        ),
        Tool(
            "list_projects",
            "read",
            "List the studio's projects (slug, name, status).",
            NoArgs,
            _list_projects,
        ),
        Tool("list_milestones", "read", "List a project's milestones.", ProjectArgs, _list_milestones),
        Tool(
            "list_tasks",
            "read",
            "List tasks, optionally for a project, milestone or status.",
            TaskListArgs,
            _list_tasks,
        ),
        Tool("get_task", "read", "Read a task by id.", IdArgs, _get_task),
        Tool(
            "create_document",
            "propose",
            "Propose a new knowledge document. It is created only if a person approves this run's work.",
            DocumentArgs,
            _create_document,
            Capability.DOCUMENTS_WRITE,
        ),
        Tool(
            "create_tasks",
            "propose",
            "Propose up to 20 new tasks in a project. They are created only if a person approves this "
            "run's work.",
            TasksArgs,
            _create_tasks,
            Capability.TASKS_CREATE,
        ),
        Tool(
            "propose_decision",
            "propose",
            "Propose a decision for the Decision Log (status 'proposed'; a person accepts it). "
            "Recorded only if "
            "a person approves this run's work.",
            DecisionArgs,
            _propose_decision,
            Capability.DECISIONS_WRITE,
        ),
    )
}

READ_TOOLS = tuple(name for name, t in TOOLS.items() if t.kind == "read")
ToolOutcome = Literal["succeeded", "failed", "denied", "limit_reached"]

"""A realistic studio built directly in the database, shared by the permission matrix and feature tests."""

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from booski_core.access.roles import Role
from booski_core.core.request_meta import utcnow
from booski_core.models import (
    Approval,
    Decision,
    Department,
    Document,
    DocumentRevision,
    Milestone,
    Project,
    ProjectMember,
    Task,
    TaskComment,
    Workstream,
)
from booski_core.modules.departments.service import seed_default_departments
from helpers import Account, add_member, make_user, make_workspace


@dataclass
class Studio:
    workspace_id: uuid.UUID
    members: dict[Role, Account]
    requester: Account  # a developer who asked for the approval
    target: Account  # a viewer that member-management actions are aimed at
    project_id: uuid.UUID
    department_id: uuid.UUID  # game-development
    workstream_id: uuid.UUID
    milestone_id: uuid.UUID
    task_id: uuid.UUID  # created by the owner, unassigned
    comment_id: uuid.UUID  # written by the owner
    document_id: uuid.UUID
    decision_id: uuid.UUID
    approval_id: uuid.UUID  # pending, requested by `requester`, no reviewer
    outsider: Account  # owner of another workspace
    other_workspace_id: uuid.UUID
    other_project_id: uuid.UUID
    other_task_id: uuid.UUID
    other_department_id: uuid.UUID


def build_studio(db: Session, *, project_visibility: str = "workspace") -> Studio:
    owner = make_user(db, "owner@booski.test")
    ws = make_workspace(db, owner, "booski", "Booski Studios")
    members = {Role.OWNER: owner}
    for role in (Role.ADMIN, Role.DEVELOPER, Role.COLLABORATOR, Role.VIEWER):
        members[role] = make_user(db, f"{role.value}@booski.test")
        add_member(db, ws, members[role], role)
    requester = make_user(db, "requester@booski.test")
    add_member(db, ws, requester, Role.DEVELOPER)
    target = make_user(db, "target@booski.test")
    add_member(db, ws, target, Role.VIEWER)

    seed_default_departments(db, ws)
    db.flush()
    department = db.query(Department).filter_by(workspace_id=ws, slug="game-development").one()
    project = Project(
        workspace_id=ws,
        slug="horizon",
        name="Project Horizon",
        project_type="Open World Survival",
        engine="Unity",
        status="prototype",
        visibility=project_visibility,
        created_by_user_id=owner.id,
    )
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=target.id, workspace_id=ws, access="contributor"))
    workstream = Workstream(
        workspace_id=ws, project_id=project.id, department_id=department.id, name="Core gameplay"
    )
    milestone = Milestone(
        workspace_id=ws, project_id=project.id, name="Vertical slice", created_by_user_id=owner.id
    )
    db.add_all([workstream, milestone])
    db.flush()
    task = Task(
        workspace_id=ws,
        project_id=project.id,
        department_id=department.id,
        workstream_id=workstream.id,
        milestone_id=milestone.id,
        title="Build the FPS controller",
        created_by_user_id=owner.id,
        position=1,
    )
    document = Document(
        workspace_id=ws,
        project_id=project.id,
        kind="design_doc",
        title="Controller design",
        created_by_user_id=owner.id,
        updated_by_user_id=owner.id,
    )
    decision = Decision(
        workspace_id=ws,
        project_id=project.id,
        title="Use Unity",
        author_user_id=owner.id,
        status="accepted",
        decided_at=utcnow(),
    )
    approval = Approval(
        workspace_id=ws,
        project_id=project.id,
        kind="code_change",
        title="Merge controller refactor",
        requested_by_user_id=requester.id,
    )
    db.add_all([task, document, decision, approval])
    db.flush()
    comment = TaskComment(workspace_id=ws, task_id=task.id, author_user_id=owner.id, body="Looks good")
    db.add_all(
        [
            comment,
            DocumentRevision(
                workspace_id=ws,
                document_id=document.id,
                revision_no=1,
                title=document.title,
                body="# Controller",
                created_by_user_id=owner.id,
            ),
        ]
    )

    outsider = make_user(db, "rival@other.test")
    other_ws = make_workspace(db, outsider, "other-studio")
    seed_default_departments(db, other_ws)
    db.flush()
    other_department = db.query(Department).filter_by(workspace_id=other_ws, slug="game-development").one()
    other_project = Project(workspace_id=other_ws, slug="rival-game", name="Rival Game")
    db.add(other_project)
    db.flush()
    other_task = Task(workspace_id=other_ws, project_id=other_project.id, title="Secret rival task")
    db.add(other_task)
    db.commit()
    return Studio(
        workspace_id=ws,
        members=members,
        requester=requester,
        target=target,
        project_id=project.id,
        department_id=department.id,
        workstream_id=workstream.id,
        milestone_id=milestone.id,
        task_id=task.id,
        comment_id=comment.id,
        document_id=document.id,
        decision_id=decision.id,
        approval_id=approval.id,
        outsider=outsider,
        other_workspace_id=other_ws,
        other_project_id=other_project.id,
        other_task_id=other_task.id,
        other_department_id=other_department.id,
    )

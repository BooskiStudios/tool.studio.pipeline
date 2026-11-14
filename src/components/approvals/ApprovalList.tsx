import { ShieldCheck } from "lucide-react";
import type { QueryValue } from "../../api/client";
import { useApprovalList, useMemberNames, useProjectIndex } from "../../api/hooks";
import type { Approval } from "../../api/types";
import { APPROVAL_KIND, APPROVAL_STATUS, timeAgo } from "../../lib/format";
import { EmptyState } from "../common";
import { LoadMore, QueryView, RefreshingHint } from "../ui";
import { statusTone } from "./ApprovalModals";

/** A live list of approval requests matching `filters` (and `only`, applied to loaded rows). */
export function ApprovalList({ filters, only, onOpen, emptyTitle, emptyText }: {
  filters: Record<string, QueryValue>;
  only?: (approval: Approval) => boolean;
  onOpen: (approval: Approval) => void;
  emptyTitle: string;
  emptyText: string;
}) {
  const approvals = useApprovalList(filters);
  const nameOf = useMemberNames();
  const projects = useProjectIndex();
  const rows = only ? approvals.items.filter(only) : approvals.items;
  return (
    <QueryView query={approvals} label="approval requests">
      {() => (
        <>
          <RefreshingHint active={approvals.isFetching && !approvals.isFetchingNextPage} />
          {rows.length === 0 ? (
            <EmptyState icon={ShieldCheck} title={emptyTitle}>{emptyText}</EmptyState>
          ) : (
            rows.map((a) => (
              <div className="approval-row" key={a.id} data-testid="approval-row">
                <span className="work-icon"><ShieldCheck size={19} aria-hidden="true" /></span>
                <div>
                  <b>{a.title}</b>
                  <small>
                    {APPROVAL_KIND[a.kind]} · {a.project_id ? projects.get(a.project_id)?.name ?? "Project" : "Studio-wide"} · requested by{" "}
                    {nameOf(a.requested_by_user_id) ?? "a former member"} {timeAgo(a.created_at)}
                  </small>
                </div>
                <span className={`pill pill-${statusTone(a.status)}`}>{APPROVAL_STATUS[a.status]}</span>
                <button type="button" className="secondary-btn" onClick={() => onOpen(a)}>{a.can_decide ? "Review" : "Open"}</button>
              </div>
            ))
          )}
          <LoadMore {...approvals} />
        </>
      )}
    </QueryView>
  );
}

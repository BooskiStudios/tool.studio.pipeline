import { ArrowUpRight, BookOpen } from "lucide-react";
import type { QueryValue } from "../../api/client";
import { useDocumentList, useMemberNames, useProjectIndex } from "../../api/hooks";
import type { DocumentSummary } from "../../api/types";
import { DOCUMENT_KIND, timeAgo } from "../../lib/format";
import { EmptyState } from "../common";
import { LoadMore, QueryView, RefreshingHint } from "../ui";

/** A live list of knowledge documents matching `filters`; selecting one calls `onOpen`. */
export function DocumentList({ filters, onOpen, emptyTitle = "No documents yet", emptyText }: {
  filters: Record<string, QueryValue>;
  onOpen: (document: DocumentSummary) => void;
  emptyTitle?: string;
  emptyText?: string;
}) {
  const documents = useDocumentList(filters);
  const projects = useProjectIndex();
  const nameOf = useMemberNames();
  return (
    <QueryView query={documents} label="documents">
      {() =>
        documents.items.length === 0 ? (
          <EmptyState icon={BookOpen} title={emptyTitle}>{emptyText ?? "Documents you create will appear here."}</EmptyState>
        ) : (
          <>
            <RefreshingHint active={documents.isFetching && !documents.isFetchingNextPage} />
            {documents.items.map((d) => {
              const project = d.project_id ? projects.get(d.project_id) : undefined;
              return (
                <div className="knowledge-doc" key={d.id} data-testid="document-row">
                  <span className="work-icon"><BookOpen size={18} aria-hidden="true" /></span>
                  <div>
                    <b>{d.title}{d.archived_at ? " (archived)" : ""}</b>
                    <small>
                      {DOCUMENT_KIND[d.kind]} · revision {d.current_revision} · edited {timeAgo(d.updated_at)} by{" "}
                      {nameOf(d.updated_by_user_id) ?? "a former member"}
                      {d.summary ? ` · ${d.summary}` : ""}
                    </small>
                  </div>
                  <span>{project ? project.name : "Studio-wide"}</span>
                  <button type="button" onClick={() => onOpen(d)} aria-label={`Open ${d.title}`}>
                    <ArrowUpRight size={15} aria-hidden="true" />
                  </button>
                </div>
              );
            })}
            <LoadMore {...documents} />
          </>
        )
      }
    </QueryView>
  );
}

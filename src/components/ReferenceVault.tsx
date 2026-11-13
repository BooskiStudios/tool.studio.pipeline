import { ArrowUpRight, Image, Plus } from "lucide-react";
import { useToast } from "../context/ToastContext";
import { useResource } from "../hooks/useResource";
import { studioApi } from "../services";
import { ResourceView } from "./common";

/** Project-specific references (Project Workspace → Reference Vault tab). */
export function ReferenceVault({ projectSlug }: { projectSlug: string }) {
  const notify = useToast();
  const references = useResource(() => studioApi.listProjectReferences(projectSlug), [projectSlug]);

  return (
    <div className="reference-vault">
      <div className="vault-toolbar">
        <p>References collected by Booski or saved by you for this project.</p>
        <button type="button" className="primary-btn" onClick={() => notify("Reference upload and URL capture will be connected to project storage.")}>
          <Plus size={14} aria-hidden="true" /> Add reference
        </button>
      </div>
      <ResourceView resource={references} label="references">
        {(rows) =>
          rows.map((r) => (
            <div className="reference-row" key={r.id}>
              <span className="work-icon"><Image size={18} aria-hidden="true" /></span>
              <span>
                <b>{r.title}</b>
                <small>{r.detail}</small>
              </span>
              <em>{r.source}</em>
              <ArrowUpRight size={15} className="muted-text" aria-hidden="true" />
            </div>
          ))
        }
      </ResourceView>
    </div>
  );
}

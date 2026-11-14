import { ArrowUpRight, Image, Plus } from "lucide-react";
import { useToast } from "../context/ToastContext";
import { useResource } from "../hooks/useResource";
import { studioApi } from "../services";
import { ResourceView } from "./common";

/**
 * Project Workspace → Reference Vault. PREVIEW: collecting references needs file storage and AI
 * research, both planned for later phases, so this shows labelled examples rather than stored records.
 */
export function ReferenceVault({ projectSlug }: { projectSlug: string }) {
  const notify = useToast();
  const references = useResource(() => studioApi.listProjectReferences(projectSlug), [projectSlug]);

  return (
    <div className="reference-vault">
      <div className="vault-toolbar">
        <p><span className="demo-label">PREVIEW · LATER PHASE</span> Examples of references Booski will collect or you will save for this project.</p>
        <button type="button" className="secondary-btn" onClick={() => notify("Reference upload and link capture arrive with file storage in a later phase.")}>
          <Plus size={14} aria-hidden="true" /> Add reference · planned
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
              <em>{r.source} · example</em>
              <ArrowUpRight size={15} className="muted-text" aria-hidden="true" />
            </div>
          ))
        }
      </ResourceView>
    </div>
  );
}

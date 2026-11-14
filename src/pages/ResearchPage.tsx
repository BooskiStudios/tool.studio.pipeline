import { useState } from "react";
import { ArrowUpRight, FileText, Upload } from "lucide-react";
import { ResourceView } from "../components/common";
import { useToast } from "../context/ToastContext";
import { useResource } from "../hooks/useResource";
import { studioApi } from "../services";

const ACCEPTED_TYPES = ".pdf,.doc,.docx,.txt,.md,.csv,.xlsx,.pptx";

/**
 * `/research` — the research document library.
 *
 * DEMO BEHAVIOUR: the upload button only reads the chosen file's name. The file
 * is not uploaded, stored or processed.
 */
export function ResearchPage() {
  const notify = useToast();
  const docs = useResource(() => studioApi.listResearchDocs(), []);
  const [uploadName, setUploadName] = useState("");

  return (
    <div className="workspace-page">
      <div className="simple-page-heading">
        <span className="eyebrow">SHARED KNOWLEDGE / RESEARCH</span>
        <h1>Research Library</h1>
        <p>Source material and research documents produced by Booski during market research, plus your own uploaded research.</p>
      </div>
      <div className="research-actions">
        <label className="upload-button">
          <Upload size={16} aria-hidden="true" /> Upload research
          <input
            type="file"
            accept={ACCEPTED_TYPES}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) {
                setUploadName(file.name);
                notify(`${file.name} selected. File storage will be connected in the backend phase.`);
              }
            }}
          />
        </label>
        <span>{uploadName ? `Selected: ${uploadName}` : "Supported: PDF, DOCX, TXT, MD, CSV, XLSX, PPTX"}</span>
      </div>
      <ResourceView resource={docs} label="research">
        {(rows) => (
          <div className="research-grid">
            {rows.map((r) => (
              <article className="panel research-card" key={r.id}>
                <div className="research-file-icon"><FileText size={22} aria-hidden="true" /></div>
                <div>
                  <b>{r.title}</b>
                  <small>{r.detail}</small>
                </div>
                <span>{r.format}</span>
                <button type="button" onClick={() => notify(`Opening ${r.title} is a future file-library capability.`)} aria-label={`Open ${r.title}`}>
                  <ArrowUpRight size={15} aria-hidden="true" />
                </button>
              </article>
            ))}
          </div>
        )}
      </ResourceView>
      <p className="small-note">Sample research entries are illustrative. Uploaded files are not yet persisted or processed in this prototype.</p>
    </div>
  );
}

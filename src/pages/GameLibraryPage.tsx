import { useState } from "react";
import { useNavigate } from "react-router";
import { ArrowUpRight, SearchX } from "lucide-react";
import { EmptyState, matchesQuery, SearchField } from "../components/common";
import { useProjects } from "../context/ProjectContext";
import { ErrorState } from "../components/ui";
import { PROJECT_STATUS, projectImage } from "../lib/format";
import { paths } from "../routes";

/** `/library` — the studio's games as a browsable library. */
export function GameLibraryPage() {
  const navigate = useNavigate();
  const { projects, error, refetch } = useProjects();
  const [query, setQuery] = useState("");
  const visible = (projects ?? []).filter((p) => matchesQuery(query, p.name, p.project_type, PROJECT_STATUS[p.status], p.engine));
  const count = projects ? `${visible.length} ${visible.length === 1 ? "title" : "titles"}` : "Loading…";

  return (
    <div className="workspace-page">
      <div className="simple-page-heading">
        <span className="eyebrow">BOOSKI STUDIOS / LIBRARY</span>
        <h1>Game Library</h1>
        <p>Your studio's games and prototypes, presented as a browsable library. Select a title to open its workspace.</p>
      </div>
      <div className="library-toolbar">
        <SearchField value={query} onChange={setQuery} placeholder="Search your library..." />
        <span aria-live="polite">{count}</span>
      </div>
      {error ? (
        <ErrorState error={error} label="your games" onRetry={refetch} />
      ) : projects && visible.length === 0 ? (
        <EmptyState icon={SearchX} title="No titles found">{query ? `No games or prototypes match “${query}”.` : "No projects yet."}</EmptyState>
      ) : (
        <div className="game-library-grid">
          {visible.map((p) => (
            <button type="button" className="game-library-card" key={p.id} onClick={() => navigate(paths.project(p.slug))}>
              <div className="library-cover">
                <img src={projectImage(p)} alt="" />
                <span>{PROJECT_STATUS[p.status]}</span>
              </div>
              <div className="library-info">
                <b>{p.name}</b>
                <small>{p.project_type || "Project"}</small>
                <div className="library-progress"><span style={{ width: `${p.progress.percent}%` }} /></div>
                <div>
                  <small>{p.engine ? `${p.engine} · ` : ""}{p.progress.percent}% complete</small>
                  <ArrowUpRight size={15} aria-hidden="true" />
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

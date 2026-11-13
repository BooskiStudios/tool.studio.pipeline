import { Plus } from "lucide-react";
import { TaskRecord } from "../components/TaskRecord";
import { useTasks } from "../context/TasksContext";

/** `/tasks` — every session task across the studio. */
export function TaskCentrePage() {
  const { tasks, toggleTask, openTaskForm } = useTasks();
  return (
    <div className="workspace-page">
      <div className="simple-page-heading">
        <span className="eyebrow">STUDIO OPERATIONS</span>
        <h1>Task Centre</h1>
        <p>One place to review and manage work across the studio.</p>
      </div>
      <section className="panel task-centre">
        {tasks ? tasks.map((t) => <TaskRecord key={t.id} task={t} onToggle={toggleTask} />) : <div className="resource-state" role="status">Loading tasks…</div>}
        <button type="button" className="primary-btn" onClick={openTaskForm}><Plus size={14} aria-hidden="true" /> New task</button>
      </section>
      <p className="small-note">Demo tasks. Additions and changes are held in memory only and reset when the page is refreshed.</p>
    </div>
  );
}

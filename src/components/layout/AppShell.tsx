import { useCallback, useState } from "react";
import { useLocation, useOutlet } from "react-router";
import { AnimatePresence, motion } from "framer-motion";
import { useTasks } from "../../context/TasksContext";
import { useWorkspace } from "../../workspace/WorkspaceProvider";
import { ProjectFormModal } from "../projects/ProjectFormModal";
import { TaskFormModal } from "../TaskFormModal";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

/**
 * Keeps rendering the page that was active when this component mounted, so the
 * outgoing page stays visible during its exit animation instead of switching to
 * the incoming route's content.
 */
function FrozenOutlet() {
  const outlet = useOutlet();
  const [frozen] = useState(outlet);
  return frozen;
}

/** Sidebar + top bar frame that every page renders inside. */
export function AppShell() {
  const location = useLocation();
  const { isTaskFormOpen } = useTasks();
  const { name } = useWorkspace();
  const [showProjectModal, setShowProjectModal] = useState(false);
  const closeProjectModal = useCallback(() => setShowProjectModal(false), []);

  return (
    <div className="app-shell">
      <Sidebar onNewProject={() => setShowProjectModal(true)} />
      <main className="main-area">
        <Topbar />
        <AnimatePresence mode="wait" onExitComplete={() => window.scrollTo(0, 0)}>
          <motion.div
            key={location.pathname}
            className="page-transition"
            initial={{ opacity: 0, y: 9 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
          >
            <FrozenOutlet />
          </motion.div>
        </AnimatePresence>

        {isTaskFormOpen && <TaskFormModal />}
        {showProjectModal && <ProjectFormModal onClose={closeProjectModal} />}

        <footer>
          BOOSKI STUDIOS <span>•</span> STUDIO OS V0.9 <span>•</span> CONNECTED TO BOOSKI CORE <span>•</span> {name.toUpperCase()}
          <span>•</span> AI FEATURES ARE PREVIEWS UNTIL PHASE 3
        </footer>
      </main>
    </div>
  );
}

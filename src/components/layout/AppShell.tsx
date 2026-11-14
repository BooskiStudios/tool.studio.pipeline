import { useCallback, useState } from "react";
import { useLocation, useOutlet } from "react-router";
import { AnimatePresence, motion } from "framer-motion";
import { useTasks } from "../../context/TasksContext";
import { studioApi } from "../../services";
import { Modal } from "../Modal";
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
        {showProjectModal && (
          <Modal
            title="New project"
            description="Project creation will be connected to the persistent backend in a later phase."
            onClose={closeProjectModal}
          >
            <button type="button" className="primary-btn" data-autofocus onClick={closeProjectModal}>Got it</button>
          </Modal>
        )}

        <footer>
          BOOSKI STUDIOS <span>•</span> FRONTEND FOUNDATION V0.8 <span>•</span>{" "}
          {studioApi.mode === "demo" ? "DEMO DATA — NOT CONNECTED TO LIVE SYSTEMS" : "CONNECTED TO BOOSKI CORE"}
        </footer>
      </main>
    </div>
  );
}

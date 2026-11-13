import { useNavigate } from "react-router";
import { Compass } from "lucide-react";
import { EmptyState } from "../components/common";
import { paths } from "../routes";

/** Shown for unknown URLs, departments and projects. */
export function NotFoundPage() {
  const navigate = useNavigate();
  return (
    <div className="workspace-page">
      <div className="simple-page-heading">
        <span className="eyebrow">BOOSKI STUDIOS</span>
        <h1>Page not found</h1>
        <p>This page doesn’t exist, or the project or department it refers to isn’t available.</p>
      </div>
      <div className="panel">
        <EmptyState
          icon={Compass}
          title="Nothing here"
          action={<button type="button" className="primary-btn" onClick={() => navigate(paths.home)}>Back to Command Centre</button>}
        >
          Check the address, or use the sidebar to find your way back.
        </EmptyState>
      </div>
    </div>
  );
}

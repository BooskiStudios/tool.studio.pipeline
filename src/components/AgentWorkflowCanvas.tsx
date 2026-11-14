import { useId, useRef, useState, type PointerEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { AgentNode } from "../types";
import { Icon } from "./Icon";

/** Curved routes from the Orchestrator out to each specialist. */
const outboundPaths = ["M50 18 C42 24 22 27 13 40", "M50 18 C48 25 40 29 38 40", "M50 18 C53 25 61 29 63 40", "M50 18 C61 23 81 28 88 40"];
/** Return routes from each specialist into Quality review. */
const reviewPaths = ["M13 52 C17 67 36 68 50 76", "M38 52 C39 65 45 69 50 76", "M63 52 C61 65 55 69 50 76", "M88 52 C83 67 64 68 50 76"];

interface DragState {
  pointerId: number;
  startX: number;
  startY: number;
  originX: number;
  originY: number;
}

/**
 * Illustrative agent workflow diagram for Studio Operations.
 *
 * Drag the background to pan. Hover or keyboard-focus (Tab) an agent to see its
 * demo workload. Not connected to live agent execution.
 */
export function AgentWorkflowCanvas({ agents }: { agents: AgentNode[] }) {
  const detailId = useId();
  const [hovered, setHovered] = useState<string | null>(null);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const drag = useRef<DragState | null>(null);
  const active = agents.find((a) => a.name === hovered);

  const startPan = (e: PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    drag.current = { pointerId: e.pointerId, startX: e.clientX, startY: e.clientY, originX: pan.x, originY: pan.y };
    e.currentTarget.setPointerCapture(e.pointerId);
    setIsDragging(true);
  };
  const movePan = (e: PointerEvent<HTMLDivElement>) => {
    const d = drag.current;
    if (!d || d.pointerId !== e.pointerId) return;
    setPan({ x: d.originX + e.clientX - d.startX, y: d.originY + e.clientY - d.startY });
  };
  const stopPan = (e: PointerEvent<HTMLDivElement>) => {
    if (drag.current?.pointerId !== e.pointerId) return;
    drag.current = null;
    setIsDragging(false);
  };

  return (
    <>
      <div className="canvas-instructions">
        <span>↔ Drag to move around the canvas</span>
        <span>Hover or Tab to an agent to inspect its current tasks</span>
      </div>
      <div
        className={`agent-canvas ${isDragging ? "is-dragging" : ""}`}
        onPointerDown={startPan}
        onPointerMove={movePan}
        onPointerUp={stopPan}
        onPointerCancel={stopPan}
        onLostPointerCapture={stopPan}
        style={{ cursor: isDragging ? "grabbing" : "grab", touchAction: "none" }}
      >
        <div className="agent-canvas-world" style={{ transform: `translate(${pan.x}px, ${pan.y}px)` }}>
          <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
            <defs>
              <filter id="flowGlow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation=".75" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
              <linearGradient id="flowGradient">
                <stop offset="0%" stopColor="#f52a9b" />
                <stop offset="55%" stopColor="#55d9f1" />
                <stop offset="100%" stopColor="#a6f47b" />
              </linearGradient>
            </defs>
            {outboundPaths.map((d, i) => (
              <motion.path
                key={d}
                d={d}
                stroke="url(#flowGradient)"
                strokeWidth=".65"
                fill="none"
                filter="url(#flowGlow)"
                strokeLinecap="round"
                strokeDasharray="2 1.5"
                animate={{ strokeDashoffset: [0, -14], opacity: [0.65, 1, 0.65] }}
                transition={{ duration: 2.2 + i * 0.35, repeat: Infinity, ease: "linear" }}
              />
            ))}
            {reviewPaths.map((d, i) => (
              <motion.path
                key={d}
                d={d}
                stroke="#4b9bb9"
                strokeWidth=".42"
                fill="none"
                opacity=".55"
                strokeDasharray="1 2"
                animate={{ strokeDashoffset: [0, 12] }}
                transition={{ duration: 3 + i * 0.3, repeat: Infinity, ease: "linear" }}
              />
            ))}
          </svg>
          <div role="list" aria-label="AI agents">
            {agents.map((a, i) => (
              <motion.div
                key={a.name}
                role="listitem"
                tabIndex={0}
                aria-label={`${a.name}: ${a.role}`}
                aria-describedby={hovered === a.name ? detailId : undefined}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.07, duration: 0.25 }}
                className={`agent-node node-${i} ${hovered === a.name ? "agent-hover" : ""}`}
                style={{ left: `${a.x}%`, top: `${a.y}%` }}
                onPointerEnter={() => setHovered(a.name)}
                onPointerLeave={() => setHovered(null)}
                onFocus={() => setHovered(a.name)}
                onBlur={() => setHovered(null)}
              >
                <span className="agent-node-icon"><Icon name={a.icon} size={18} /></span>
                <b>{a.name}</b>
                <small>{a.role}</small>
                <i aria-hidden="true" />
              </motion.div>
            ))}
          </div>
        </div>
        <div aria-live="polite">
          <AnimatePresence>
            {active && (
              <motion.div
                key={active.name}
                id={detailId}
                className="agent-detail"
                initial={{ opacity: 0, x: 8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 8 }}
                transition={{ duration: 0.18 }}
              >
                <span className="eyebrow">CURRENT TASKS</span>
                <b>{active.name}</b>
                <small>{active.role}</small>
                <ul>
                  {active.tasks.map((t) => <li key={t}>{t}</li>)}
                </ul>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        <div className="canvas-legend" aria-hidden="true">
          <span><i className="legend-dot green-dot" /> Working</span>
          <span><i className="legend-dot blue-dot" /> Coordinating</span>
          <span><i className="legend-dot grey-dot" /> Awaiting input</span>
        </div>
      </div>
    </>
  );
}

import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { SlidersHorizontal } from "lucide-react";
import { PageHeading, ResourceView } from "../components/common";
import { useToast } from "../context/ToastContext";
import { useResource } from "../hooks/useResource";
import { studioApi } from "../services";

const tooltipStyle = { background: "#071725", border: "1px solid #31536b", borderRadius: 8, color: "#fff" };
const axisTick = { fill: "#9bb0c2", fontSize: 10 };
const valueTick = { fill: "#8199ad", fontSize: 9 };
const chartMargin = { top: 8, right: 8, left: -18, bottom: 5 };

/** `/cost-usage` — AI consumption and cost reporting (illustrative). */
export function CostUsagePage() {
  const notify = useToast();
  const report = useResource(() => studioApi.getUsageReport(), []);

  return (
    <div className="workspace-page">
      <PageHeading
        eyebrow="BOOSKI AI CORE / FINANCIALS"
        title="Cost & Usage"
        description="Understand AI consumption and operating costs across providers, agents, workflows and projects."
        source="planned"
      />
      <div className="demo-chart-note">
        <span className="demo-label">ILLUSTRATIVE DATA</span> Charts demonstrate the intended reporting layout; they are not actual provider charges or usage.
      </div>
      <ResourceView resource={report} label="usage">
        {({ summary, byDepartment, weeklySpend }) => (
          <>
            <div className="usage-summary-grid">
              {summary.map((s) => (
                <article className="panel usage-summary" key={s.label}>
                  <small>{s.label}</small>
                  <b>{s.value}</b>
                  <span>{s.note}</span>
                </article>
              ))}
            </div>
            <div className="usage-columns">
              <section className="panel">
                <div className="panel-title"><h2>Usage by department</h2><span className="demo-label">SAMPLE</span></div>
                <div className="chart-wrap">
                  <ResponsiveContainer width="100%" height={230}>
                    <BarChart data={byDepartment} margin={chartMargin}>
                      <CartesianGrid stroke="#1c3a50" strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="name" tick={axisTick} axisLine={false} tickLine={false} />
                      <YAxis tick={valueTick} axisLine={false} tickLine={false} />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Bar dataKey="tokens" name="Usage (k tokens)" fill="#42cce7" radius={[5, 5, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </section>
              <section className="panel">
                <div className="panel-title"><h2>Illustrative weekly spend</h2><span className="demo-label">SAMPLE</span></div>
                <div className="chart-wrap">
                  <ResponsiveContainer width="100%" height={230}>
                    <AreaChart data={weeklySpend} margin={chartMargin}>
                      <defs>
                        <linearGradient id="costFill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#ed329b" stopOpacity={0.38} />
                          <stop offset="100%" stopColor="#ed329b" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid stroke="#1c3a50" strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="period" tick={axisTick} axisLine={false} tickLine={false} />
                      <YAxis tick={valueTick} axisLine={false} tickLine={false} />
                      <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`£${Number(v).toFixed(2)}`, "Spend"]} />
                      <Area type="monotone" dataKey="cost" stroke="#f34aa9" strokeWidth={2} fill="url(#costFill)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </section>
            </div>
          </>
        )}
      </ResourceView>
      <div className="panel budget-controls">
        <div className="panel-title"><h2>Budget controls</h2></div>
        <p className="muted-copy">Set monthly limits, per-agent spending thresholds and approval requirements before connecting paid providers.</p>
        <button type="button" className="primary-btn" onClick={() => notify("Budget settings will be persisted in Booski Core.")}>
          Configure budgets <SlidersHorizontal size={14} aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}

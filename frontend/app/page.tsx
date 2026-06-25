import Link from "next/link";
import { api, Decision, Funnel, inr, pct, Roi } from "../lib/api";

export default async function Dashboard() {
  const [funnel, roi, decisions] = await Promise.all([
    api<Funnel>("/analytics/funnel"),
    api<Roi>("/analytics/roi"),
    api<Decision[]>("/decisions?limit=10"),
  ]);

  return (
    <>
      <h2>Dashboard</h2>
      <p className="page-sub">Live view of the CLR funnel, ROI and recent decisions.</p>

      <div className="grid cols-4">
        <Metric label="Customers eligible" value={funnel.eligible.toString()} />
        <Metric label="Decisions reviewed" value={funnel.reviewed.toString()} />
        <Metric label="HITL pending" value={funnel.hitl_pending.toString()} sub="Awaiting maker-checker" />
        <Metric label="Executed" value={funnel.executed.toString()} sub="Limit write-back complete" />
      </div>

      <div style={{ height: 16 }} />

      <div className="grid cols-4">
        <Metric label="Upgrades" value={funnel.upgrade_recommended.toString()} accent="green" />
        <Metric label="Downgrades" value={funnel.downgrade_recommended.toString()} accent="red" />
        <Metric label="Freezes" value={funnel.freeze_recommended.toString()} accent="amber" />
        <Metric label="Benefits tier bumps" value={roi.benefits_tier_upgrades.toString()} sub="Atomic limit + tier upgrade" />
      </div>

      <div style={{ height: 24 }} />

      <h3 style={{ margin: "0 0 12px" }}>ROI & risk <span className="layer-badge">L7</span></h3>
      <div className="grid cols-4">
        <Metric label="Total limit uplift" value={inr(roi.total_limit_uplift_inr)} sub="Executed upgrades only" />
        <Metric label="Est. incremental interchange / mo" value={inr(roi.estimated_incremental_interchange_monthly_inr)} sub="Assumes 40% spend ratio @ 120 bps" />
        <Metric label="Avg PD pre" value={pct(roi.avg_pd_pre)} />
        <Metric label="Avg PD post" value={pct(roi.avg_pd_post)} accent={roi.avg_pd_post <= roi.avg_pd_pre ? "green" : "red"} />
      </div>

      <div className="divider" />

      <div className="row" style={{ justifyContent: "space-between", marginBottom: 12 }}>
        <h3 style={{ margin: 0 }}>Recent decisions</h3>
        <Link href="/customers" className="btn">All customers →</Link>
      </div>
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead>
            <tr>
              <th>Decision</th>
              <th>Customer</th>
              <th>Trigger</th>
              <th>Limit change</th>
              <th>PD</th>
              <th>HITL</th>
              <th>When</th>
            </tr>
          </thead>
          <tbody>
            {decisions.map((d) => (
              <tr key={d.id}>
                <td><span className={`badge badge-${d.decision}`}>{d.decision}</span></td>
                <td><Link href={`/customers/${d.customer_id}`}>{d.customer_id}</Link></td>
                <td className="muted">{d.trigger_type}</td>
                <td>
                  {d.decision === "FREEZE"
                    ? <span className="muted">{inr(d.current_limit)}</span>
                    : <>{inr(d.current_limit)} → <strong>{inr(d.recommended_limit)}</strong></>}
                </td>
                <td className="muted">{pct(d.pd_pre)} → {pct(d.pd_post_projected)}</td>
                <td><span className={`badge badge-${d.hitl_status}`}>{d.hitl_status}</span></td>
                <td className="muted">{new Date(d.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function Metric({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent?: "green" | "red" | "amber" }) {
  const color = accent === "green" ? "var(--green)" : accent === "red" ? "var(--red)" : accent === "amber" ? "var(--amber)" : undefined;
  return (
    <div className="card">
      <div className="metric-label">{label}</div>
      <div className="metric-value" style={{ color }}>{value}</div>
      {sub && <div className="metric-sub">{sub}</div>}
    </div>
  );
}

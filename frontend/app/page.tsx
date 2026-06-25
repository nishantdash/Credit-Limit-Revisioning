import Link from "next/link";
import { api, Decision, Funnel, inr, pct, Roi } from "../lib/api";
import { MetricCard } from "../components/MetricCard";
import { Pill } from "../components/Pill";
import { Avatar } from "../components/Avatar";
import { Icon } from "../components/Icon";

export default async function Dashboard() {
  const [funnel, roi, decisions, pending] = await Promise.all([
    api<Funnel>("/analytics/funnel"),
    api<Roi>("/analytics/roi"),
    api<Decision[]>("/decisions?limit=8"),
    api<Decision[]>("/hitl/queue"),
  ]);

  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  const reviewedPct = funnel.eligible ? (funnel.reviewed / funnel.eligible) * 100 : 0;

  return (
    <>
      <div className="page-head">
        <div>
          <h2 className="page-title">{greeting}, Nishant</h2>
          <p className="page-sub" style={{ marginBottom: 0 }}>Here's what's happening across the YES Bank programme today.</p>
        </div>
        <div className="actions">
          <button className="btn"><Icon name="download" size={14} /> Export</button>
          <Link href="/triggers" className="btn btn-primary"><Icon name="plus" size={14} /> Run sweep</Link>
        </div>
      </div>

      <div className="grid cols-4">
        <MetricCard
          label="Customers eligible"
          value={funnel.eligible.toString()}
          sub={`${funnel.reviewed} reviewed this cycle`}
          delta={funnel.reviewed > 0 ? { value: `${reviewedPct.toFixed(0)}% coverage`, direction: "up" } : undefined}
          iconName="users"
        />
        <MetricCard
          label="Recommended uplift"
          value={inr(roi.total_limit_uplift_inr)}
          sub={`${roi.upgrades_count} upgrades executed`}
          iconName="trend-up"
        />
        <MetricCard
          label="HITL pending"
          value={funnel.hitl_pending.toString()}
          sub="Awaiting maker-checker"
          iconName="checklist"
        />
        <MetricCard
          label="Avg PD shift"
          value={`${(roi.avg_pd_pre * 100).toFixed(2)}% → ${(roi.avg_pd_post * 100).toFixed(2)}%`}
          sub={roi.avg_pd_post <= roi.avg_pd_pre ? "PD held flat or improved" : "PD increased"}
          delta={roi.avg_pd_post <= roi.avg_pd_pre
            ? { value: "within threshold", direction: "up" }
            : { value: "watch", direction: "down" }}
          iconName="shield"
        />
      </div>

      <div style={{ height: 24 }} />

      <div className="grid split-2-1">
        <div className="card padless">
          <div className="card-head">
            <div className="row" style={{ gap: 8 }}>
              <h3>Needs attention</h3>
              <Pill variant="red" bare>{pending.length} open</Pill>
            </div>
            <Link href="/hitl" className="btn btn-sm">Open queue</Link>
          </div>
          <div className="card-body">
            {pending.length === 0 ? (
              <div className="empty">All HITL items cleared. The maker-checker queue is empty.</div>
            ) : (
              pending.slice(0, 5).map((d) => (
                <div key={d.id} className="na-row">
                  <div className="na-icon"><Icon name="alert-circle" size={18} /></div>
                  <div className="na-text">
                    <div className="na-title">
                      {d.customer_id} — {d.decision} {inr(d.current_limit)} → {inr(d.recommended_limit)}
                    </div>
                    <div className="na-meta">
                      Trigger: {d.trigger_type} · PD {pct(d.pd_pre)} → {pct(d.pd_post_projected)} · {d.reason_codes.slice(0, 2).join(", ")}
                    </div>
                  </div>
                  <Pill variant="purple" bare>HITL · {d.hitl_status}</Pill>
                  <Link href={`/customers/${d.customer_id}`} className="btn btn-sm">Review <Icon name="arrow-right" size={12} /></Link>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="card">
          <h3 style={{ marginBottom: 12 }}>Quick actions</h3>
          <Link href="/triggers" className="qa-item" style={{ textDecoration: "none", color: "inherit" }}>
            <div className="qa-icon"><Icon name="bolt" size={18} /></div>
            <div>
              <div className="qa-title">Run periodic sweep</div>
              <div className="qa-sub">Monthly batch across the book</div>
            </div>
            <Icon name="arrow-right" size={16} className="qa-arrow" />
          </Link>
          <Link href="/ingest" className="qa-item" style={{ textDecoration: "none", color: "inherit" }}>
            <div className="qa-icon"><Icon name="upload" size={18} /></div>
            <div>
              <div className="qa-title">Upload transaction dump</div>
              <div className="qa-sub">CSV → cohort sweep</div>
            </div>
            <Icon name="arrow-right" size={16} className="qa-arrow" />
          </Link>
          <Link href="/hitl" className="qa-item" style={{ textDecoration: "none", color: "inherit" }}>
            <div className="qa-icon"><Icon name="checklist" size={18} /></div>
            <div>
              <div className="qa-title">Review pending HITL</div>
              <div className="qa-sub">{funnel.hitl_pending} awaiting approval</div>
            </div>
            <Icon name="arrow-right" size={16} className="qa-arrow" />
          </Link>
          <Link href="/audit" className="qa-item" style={{ textDecoration: "none", color: "inherit" }}>
            <div className="qa-icon"><Icon name="audit" size={18} /></div>
            <div>
              <div className="qa-title">Audit log</div>
              <div className="qa-sub">Immutable RBI / DPDP trail</div>
            </div>
            <Icon name="arrow-right" size={16} className="qa-arrow" />
          </Link>
        </div>
      </div>

      <div style={{ height: 24 }} />

      <div className="card padless">
        <div className="card-head">
          <h3>Recent decisions</h3>
          <Link href="/customers" className="btn btn-sm">All customers <Icon name="arrow-right" size={12} /></Link>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Decision</th>
                <th>Customer</th>
                <th>Trigger</th>
                <th>Limit change</th>
                <th>PD pre → post</th>
                <th>Status</th>
                <th>When</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {decisions.map((d) => (
                <tr key={d.id}>
                  <td><Pill variant={d.decision}>{d.decision}</Pill></td>
                  <td>
                    <Link href={`/customers/${d.customer_id}`} style={{ color: "var(--text)" }} className="row" >
                      <Avatar id={d.customer_id} size="sm" />
                      <span style={{ marginLeft: 8 }}>{d.customer_id}</span>
                    </Link>
                  </td>
                  <td className="muted">{d.trigger_type}</td>
                  <td>
                    {d.decision === "FREEZE"
                      ? <span className="muted">{inr(d.current_limit)}</span>
                      : <>{inr(d.current_limit)} <Icon name="arrow-right" size={12} /> <strong>{inr(d.recommended_limit)}</strong></>}
                  </td>
                  <td className="muted">{pct(d.pd_pre)} → {pct(d.pd_post_projected)}</td>
                  <td>
                    {d.hitl_required
                      ? <Pill variant={d.hitl_status as "PENDING" | "APPROVED" | "REJECTED"}>{d.hitl_status}</Pill>
                      : d.executed
                        ? <Pill variant="EXECUTED">EXECUTED</Pill>
                        : <Pill variant="gray" bare>auto</Pill>}
                  </td>
                  <td className="muted">{new Date(d.created_at).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</td>
                  <td><Icon name="chevron-right" size={14} className="muted" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

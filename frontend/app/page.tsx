import Link from "next/link";
import {
  api, Decision, Funnel, Guardrails, inr, inrCompact, Roi,
  DIRECTION_VARIANT, INTENT_VARIANT, TIER_LABEL,
} from "../lib/api";
import { MetricCard } from "../components/MetricCard";
import { Pill } from "../components/Pill";
import { Avatar } from "../components/Avatar";
import { Icon } from "../components/Icon";
import { DistBar, colorFor } from "../components/DistBar";

const INTENT_ORDER = ["GROWTH", "DISTRESS", "SEASONAL", "NEUTRAL", "KNOCKOUT"];
const TIER_ORDER = ["tier1", "tier2", "tier3", "tier4"];

export default async function Dashboard() {
  const [funnel, roi, guard, decisions] = await Promise.all([
    api<Funnel>("/analytics/funnel"),
    api<Roi>("/analytics/roi"),
    api<Guardrails>("/analytics/guardrails"),
    api<Decision[]>("/decisions?limit=10"),
  ]);

  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  const intentSegs = INTENT_ORDER.filter((k) => funnel.by_intent[k]).map((k) => ({ label: k, value: funnel.by_intent[k], color: colorFor(k) }));
  const tierSegs = TIER_ORDER.filter((k) => funnel.by_tier[k]).map((k) => ({ label: `T${k.slice(-1)}`, value: funnel.by_tier[k], color: colorFor(k) }));

  const gaugeUsed = guard.portfolio_increase_cap_pct ? (guard.portfolio_increase_used_pct / guard.portfolio_increase_cap_pct) * 100 : 0;

  return (
    <>
      <div className="page-head">
        <div>
          <h2 className="page-title">{greeting}, Nishant</h2>
          <p className="page-sub" style={{ marginBottom: 0 }}>
            Real-time credit-limit revisioning across the book — intent, not just risk.
          </p>
        </div>
        <div className="actions">
          <Link href="/matrix" className="btn"><Icon name="layers" size={14} /> Matrix</Link>
          <Link href="/triggers" className="btn btn-primary"><Icon name="bolt" size={14} /> Run micro-review</Link>
        </div>
      </div>

      <div className="grid cols-4">
        <MetricCard label="Customers in book" value={funnel.customers.toString()} sub={`${funnel.reviewed} decisions this cycle`} iconName="users" />
        <MetricCard label="Offered uplift (consent-gated)" value={inrCompact(roi.offered_uplift_inr)} sub={`${inrCompact(roi.activated_uplift_inr)} activated`} iconName="trend-up" delta={{ value: `${funnel.offers_pending_consent} awaiting OTP`, direction: "up" }} />
        <MetricCard label="Exposure reduced" value={inrCompact(roi.exposure_reduced_inr)} sub={`${funnel.actions_applied} decreases applied`} iconName="shield" />
        <MetricCard label="Avg PD shift" value={`${(roi.avg_pd_pre * 100).toFixed(2)}% → ${(roi.avg_pd_post * 100).toFixed(2)}%`} sub={roi.avg_pd_post <= roi.avg_pd_pre ? "held flat or improved" : "watch"} iconName="checklist" delta={{ value: roi.avg_pd_post <= roi.avg_pd_pre ? "within threshold" : "watch", direction: roi.avg_pd_post <= roi.avg_pd_pre ? "up" : "down" }} />
      </div>

      <div style={{ height: 24 }} />

      <div className="grid split-2-1">
        <div className="grid" style={{ gap: 24 }}>
          <div className="card">
            <div className="row-between" style={{ marginBottom: 16 }}>
              <h3>Intent disambiguation</h3>
              <span className="muted" style={{ fontSize: 12 }}>growth vs distress vs seasonal</span>
            </div>
            <DistBar segments={intentSegs} />
            <div style={{ height: 18 }} />
            <div className="row-between" style={{ marginBottom: 12 }}>
              <h3 style={{ fontSize: 14 }}>Risk tiers</h3>
              <span className="muted" style={{ fontSize: 12 }}>continuous, not period-end</span>
            </div>
            <DistBar segments={tierSegs} />
          </div>

          <div className="card padless">
            <div className="card-head">
              <h3>Recent decisions</h3>
              <Link href="/customers" className="btn btn-sm">All customers <Icon name="arrow-right" size={12} /></Link>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr><th>Customer</th><th>Cell</th><th>Intent</th><th>Decision</th><th>Limit</th><th>Pipeline</th><th>Conf</th></tr>
                </thead>
                <tbody>
                  {decisions.map((d) => (
                    <tr key={d.id}>
                      <td>
                        <Link href={`/customers/${d.customer_id}`} className="row" style={{ color: "var(--text)" }}>
                          <Avatar id={d.customer_id} size="sm" /><span style={{ marginLeft: 8 }}>{d.customer_id}</span>
                        </Link>
                      </td>
                      <td data-label="Cell" className="muted" style={{ fontSize: 12 }} title={TIER_LABEL[d.risk_tier]}>{d.matrix_cell}</td>
                      <td data-label="Intent"><Pill variant={INTENT_VARIANT[d.intent]} bare>{d.intent}</Pill></td>
                      <td data-label="Decision">
                        <Pill variant={DIRECTION_VARIANT[d.direction]}>{d.direction}</Pill>
                        {d.duration === "TEMPORARY" && <span style={{ marginLeft: 6 }}><Pill variant="TEMPORARY" bare>temp</Pill></span>}
                      </td>
                      <td data-label="Limit" className="muted" style={{ fontSize: 13 }}>
                        {d.direction === "MAINTAIN" || d.direction === "FREEZE"
                          ? inr(d.current_limit)
                          : <>{inr(d.current_limit)} <Icon name="arrow-right" size={11} /> <strong style={{ color: "var(--text)" }}>{inr(d.recommended_limit)}</strong></>}
                      </td>
                      <td data-label="Pipeline">{d.pipeline === "NONE" ? <span className="muted">—</span> : <Pill variant={d.pipeline} bare>{d.pipeline}</Pill>}</td>
                      <td data-label="Confidence" className="muted">{(d.confidence * 100).toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="grid" style={{ gap: 24, alignContent: "start" }}>
          <div className="card">
            <h3 style={{ marginBottom: 14 }}>Orchestration pipelines</h3>
            <p className="muted" style={{ fontSize: 12, marginTop: 0, marginBottom: 14 }}>
              The RBI consent asymmetry: increases are offers, decreases are actions.
            </p>
            <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div className="pipe-card">
                <span className="pipe-k" style={{ color: "var(--primary)" }}>{funnel.offers_pending_consent}</span>
                <span className="pipe-l">Offers awaiting OTP/MPIN</span>
              </div>
              <div className="pipe-card">
                <span className="pipe-k" style={{ color: "var(--green)" }}>{funnel.offers_accepted}</span>
                <span className="pipe-l">Offers accepted</span>
              </div>
              <div className="pipe-card">
                <span className="pipe-k" style={{ color: "var(--red)" }}>{funnel.actions_applied}</span>
                <span className="pipe-l">Decreases applied</span>
              </div>
              <div className="pipe-card">
                <span className="pipe-k" style={{ color: "var(--amber)" }}>{funnel.review_pending}</span>
                <span className="pipe-l">Held for review</span>
              </div>
            </div>
            <div className="row" style={{ gap: 8, marginTop: 14 }}>
              <Link href="/offers" className="btn btn-sm" style={{ flex: 1, justifyContent: "center" }}>Offers</Link>
              <Link href="/actions" className="btn btn-sm" style={{ flex: 1, justifyContent: "center" }}>Actions</Link>
              <Link href="/review" className="btn btn-sm" style={{ flex: 1, justifyContent: "center" }}>Review</Link>
            </div>
          </div>

          <div className="card">
            <div className="row-between" style={{ marginBottom: 6 }}>
              <h3>Anti-spiral guardrail</h3>
              <Pill variant={gaugeUsed > 80 ? "red" : gaugeUsed > 50 ? "amber" : "green"} bare>
                {guard.portfolio_headroom_pct.toFixed(1)}% headroom
              </Pill>
            </div>
            <p className="muted" style={{ fontSize: 12, marginTop: 0, marginBottom: 14 }}>
              Portfolio increase-velocity cap — ceiling on aggregate book uplift, independent of individual eligibility.
            </p>
            <div className="gauge-track">
              <div className="gauge-fill" style={{ width: `${Math.min(gaugeUsed, 100)}%` }} />
            </div>
            <div className="row-between" style={{ marginTop: 8, fontSize: 12 }}>
              <span className="muted">{inrCompact(guard.increase_extended_30d_inr)} extended (30d)</span>
              <span className="muted">cap {guard.portfolio_increase_cap_pct}% of {inrCompact(guard.total_book_limit_inr)}</span>
            </div>
            {Object.keys(guard.cap_breakdown).length > 0 && (
              <div className="reasons" style={{ marginTop: 12 }}>
                {Object.entries(guard.cap_breakdown).map(([k, v]) => (
                  <span key={k} className="chip">{k} · {v}</span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

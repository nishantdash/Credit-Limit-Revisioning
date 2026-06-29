import Link from "next/link";
import { api, Decision, inr, inrCompact, INTENT_VARIANT } from "../../lib/api";
import { Avatar } from "../../components/Avatar";
import { Icon } from "../../components/Icon";
import { MetricCard } from "../../components/MetricCard";
import { Pill } from "../../components/Pill";

export default async function ActionsPage() {
  const actions = await api<Decision[]>("/actions");
  const applied = actions.filter((d) => d.executed);
  const exposureCut = applied.reduce((s, d) => s + (d.current_limit - d.recommended_limit), 0);
  const knockouts = actions.filter((d) => d.intent === "KNOCKOUT").length;
  const inactivity = actions.filter((d) => d.applied_caps.includes("INACTIVITY_RIGHTSIZE")).length;

  return (
    <>
      <div className="page-head">
        <div>
          <h2 className="page-title">Action pipeline</h2>
          <p className="page-sub" style={{ marginBottom: 0 }}>
            Risk-driven decreases. RBI permits these proactively, so they are applied with a 10% operational buffer
            above outstanding and the customer is notified — no pre-approval.
          </p>
        </div>
      </div>

      <div className="grid cols-4">
        <MetricCard label="Decreases applied" value={applied.length.toString()} sub="With operational buffer" iconName="trend-down" />
        <MetricCard label="Exposure reduced" value={inrCompact(exposureCut)} sub="Capital freed" iconName="shield" />
        <MetricCard label="Knockout-driven" value={knockouts.toString()} sub="Fraud / legal / 30+ DPD" iconName="alert-circle" />
        <MetricCard label="Inactivity right-sized" value={inactivity.toString()} sub="Dormant limits" iconName="calendar" />
      </div>

      <div style={{ height: 24 }} />

      <div className="card padless">
        <div className="card-head"><h3>Applied decreases</h3><span className="muted" style={{ fontSize: 12 }}>{actions.length} total</span></div>
        {actions.length === 0 ? (
          <div className="empty">No decreases yet. Run a micro-review sweep.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Customer</th><th>Cell</th><th>Intent</th><th>Limit change</th><th>Buffer kept</th><th>PD pre → post</th><th>Drivers</th><th>Status</th></tr>
              </thead>
              <tbody>
                {actions.map((d) => {
                  const cut = d.current_limit - d.recommended_limit;
                  return (
                    <tr key={d.id}>
                      <td>
                        <Link href={`/customers/${d.customer_id}`} className="row" style={{ gap: 10, color: "var(--text)" }}>
                          <Avatar id={d.customer_id} size="sm" /><span>{d.customer_id}</span>
                        </Link>
                      </td>
                      <td className="muted" style={{ fontSize: 12 }}>{d.matrix_cell}</td>
                      <td><Pill variant={INTENT_VARIANT[d.intent]} bare>{d.intent}</Pill></td>
                      <td>
                        {inr(d.current_limit)} <Icon name="arrow-right" size={11} /> <strong>{inr(d.recommended_limit)}</strong>
                        <span style={{ color: "var(--red)", fontSize: 12, marginLeft: 6 }}>{d.magnitude_pct.toFixed(1)}%</span>
                      </td>
                      <td className="muted">{inr(cut)} freed</td>
                      <td className="muted">{(d.pd_pre * 100).toFixed(2)}% → {(d.pd_post_projected * 100).toFixed(2)}%</td>
                      <td><div className="reasons">{d.reason_codes.slice(0, 2).map((r) => <span key={r} className="chip">{r}</span>)}</div></td>
                      <td>{d.executed ? <Pill variant="ACCEPTED" bare>applied + notified</Pill> : <Pill variant="amber" bare>held</Pill>}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}

import Link from "next/link";
import { api, Customer, inrCompact, INTENT_VARIANT } from "../../lib/api";
import { Avatar } from "../../components/Avatar";
import { Icon } from "../../components/Icon";
import { MetricCard } from "../../components/MetricCard";
import { Pill } from "../../components/Pill";

type Detail = {
  customer: Customer;
  card: { current_limit: number; outstanding: number } | null;
  latest_tier: number | null;
  latest_intent: string | null;
};

export default async function CustomersPage() {
  const customers = await api<Customer[]>("/customers");
  const details = await Promise.all(customers.map((c) => api<Detail>(`/customers/${c.id}`).catch(() => null)));
  const rows = customers.map((c, i) => ({ c, d: details[i] }));

  const msme = customers.filter((c) => c.entity_type === "MSME").length;
  const flagged = customers.filter((c) => c.fraud_flag || c.legal_block_flag || c.dpd_max_12m >= 30).length;
  const noConsent = customers.filter((c) => !c.aa_consent_active).length;

  return (
    <>
      <div className="page-head">
        <div>
          <h2 className="page-title">Customers</h2>
          <p className="page-sub" style={{ marginBottom: 0 }}>{customers.length} cardholders across the retail + MSME book.</p>
        </div>
        <div className="actions">
          <Link href="/ingest" className="btn btn-primary"><Icon name="upload" size={14} /> Upload cohort</Link>
        </div>
      </div>

      <div className="grid cols-4">
        <MetricCard label="Total customers" value={customers.length.toString()} sub="Retail + MSME" iconName="users" />
        <MetricCard label="MSME" value={msme.toString()} sub="Trade-credit double-gate" iconName="spark" />
        <MetricCard label="Knockout-eligible" value={flagged.toString()} sub="Fraud / legal / 30+ DPD" iconName="alert-circle" />
        <MetricCard label="AA consent inactive" value={noConsent.toString()} sub="Degrades to internal signals" iconName="shield" />
      </div>

      <div style={{ height: 24 }} />

      <div className="card padless">
        <div className="card-head" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="input-icon-wrap" style={{ flex: 1, maxWidth: 320 }}>
            <span className="icon"><Icon name="search" size={14} /></span>
            <input placeholder="Search cardholder or CIF" />
          </div>
          <div className="row" style={{ gap: 8 }}>
            <button className="btn"><Icon name="filter" size={14} /> All entities <Icon name="chevron-down" size={12} /></button>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Cardholder</th><th>CIF</th><th>Type</th><th>Bureau</th><th>Tier</th><th>Latest intent</th><th>Limit</th><th>Utilisation</th><th></th></tr>
            </thead>
            <tbody>
              {rows.map(({ c, d }) => {
                const card = d?.card;
                const util = card?.current_limit ? (card.outstanding / card.current_limit) * 100 : 0;
                const utilColor = util > 80 ? "danger" : util > 60 ? "" : "success";
                return (
                  <tr key={c.id}>
                    <td>
                      <div className="row" style={{ gap: 10 }}>
                        <Avatar name={c.name} />
                        <div style={{ lineHeight: 1.2 }}>
                          <div style={{ fontWeight: 600, color: "var(--text)" }}>{c.name}</div>
                          <div style={{ fontSize: 11, color: "var(--text-dim)" }}>{c.employment_type.replace("_", "-").toLowerCase()}</div>
                        </div>
                      </div>
                    </td>
                    <td className="mono muted">{c.id}</td>
                    <td><Pill variant={c.entity_type} bare>{c.entity_type}</Pill></td>
                    <td><span style={{ color: c.bureau_score >= 750 ? "var(--green)" : c.bureau_score >= 700 ? "var(--text)" : "var(--amber)" }}>{c.bureau_score}</span></td>
                    <td>{d?.latest_tier ? <Pill variant={`tier${d.latest_tier}`} bare>T{d.latest_tier}</Pill> : <span className="muted">—</span>}</td>
                    <td>{d?.latest_intent ? <Pill variant={INTENT_VARIANT[d.latest_intent]} bare>{d.latest_intent}</Pill> : <span className="muted">—</span>}</td>
                    <td>{card ? inrCompact(card.current_limit) : "—"}</td>
                    <td style={{ minWidth: 150 }}>
                      {card ? (
                        <div className="row" style={{ gap: 8 }}>
                          <div className={`progress ${utilColor}`} style={{ flex: 1, maxWidth: 90 }}><div style={{ width: `${Math.min(util, 100)}%` }} /></div>
                          <span className="muted" style={{ fontSize: 12, minWidth: 30 }}>{util.toFixed(0)}%</span>
                        </div>
                      ) : "—"}
                    </td>
                    <td><Link href={`/customers/${c.id}`}><Icon name="chevron-right" size={14} className="muted" /></Link></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

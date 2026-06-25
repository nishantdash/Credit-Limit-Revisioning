import Link from "next/link";
import { api, Customer, inr } from "../../lib/api";
import { Avatar } from "../../components/Avatar";
import { Icon } from "../../components/Icon";
import { MetricCard } from "../../components/MetricCard";
import { Pill } from "../../components/Pill";

type Detail = { customer: Customer; card: { current_limit: number; current_balance: number; benefits_tier: string } | null };

export default async function CustomersPage() {
  const customers = await api<Customer[]>("/customers");
  const details = await Promise.all(
    customers.map((c) => api<Detail>(`/customers/${c.id}`).catch(() => null))
  );
  const enriched = customers.map((c, i) => ({ customer: c, card: details[i]?.card ?? null }));

  const premiumCount = customers.filter((c) => c.segment === "PREMIUM").length;
  const dpdFlagged = customers.filter((c) => c.dpd_max_12m > 0).length;
  const totalIncome = customers.reduce((s, c) => s + c.stated_income, 0);

  return (
    <>
      <div className="page-head">
        <div>
          <h2 className="page-title">Customers</h2>
          <p className="page-sub" style={{ marginBottom: 0 }}>{customers.length} eligible cardholders in the CLR roster.</p>
        </div>
        <div className="actions">
          <button className="btn"><Icon name="download" size={14} /> Export</button>
          <Link href="/ingest" className="btn btn-primary"><Icon name="upload" size={14} /> Upload cohort</Link>
        </div>
      </div>

      <div className="grid cols-4">
        <MetricCard label="Eligible" value={customers.length.toString()} sub="In the CLR roster" iconName="users" />
        <MetricCard label="Premium" value={premiumCount.toString()} sub="Tier-up eligible cohort" iconName="spark" />
        <MetricCard label="DPD flagged" value={dpdFlagged.toString()} sub="Late payment in last 12 months" iconName="alert-circle" />
        <MetricCard label="Stated income (sum)" value={inr(totalIncome)} sub={`avg ${inr(totalIncome / Math.max(customers.length, 1))}/mo`} iconName="trend-up" />
      </div>

      <div style={{ height: 24 }} />

      <div className="card padless">
        <div className="card-head" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="input-icon-wrap" style={{ flex: 1, maxWidth: 320 }}>
            <span className="icon"><Icon name="search" size={14} /></span>
            <input placeholder="Search cardholder or CIF" />
          </div>
          <div className="row" style={{ gap: 8 }}>
            <button className="btn"><Icon name="filter" size={14} /> All programmes <Icon name="chevron-down" size={12} /></button>
            <button className="btn"><Icon name="filter" size={14} /> All segments <Icon name="chevron-down" size={12} /></button>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Cardholder</th>
                <th>CIF</th>
                <th>Programme</th>
                <th>Bureau</th>
                <th>Current limit</th>
                <th>Utilisation</th>
                <th>Segment</th>
                <th>Tier</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {enriched.map(({ customer: c, card }) => {
                const util = card?.current_limit ? (card.current_balance / card.current_limit) * 100 : 0;
                const utilColor = util > 80 ? "danger" : util > 60 ? "" : "success";
                return (
                  <tr key={c.id}>
                    <td>
                      <div className="row" style={{ gap: 10 }}>
                        <Avatar name={c.name} />
                        <div style={{ lineHeight: 1.2 }}>
                          <div style={{ fontWeight: 600, color: "var(--text)" }}>{c.name}</div>
                          <div style={{ fontSize: 11, color: "var(--text-dim)" }}>{c.employment_type === "SELF_EMPLOYED" ? "Self-employed" : "Salaried"}</div>
                        </div>
                      </div>
                    </td>
                    <td className="mono muted">{c.id}</td>
                    <td className="muted">{c.programme_id}</td>
                    <td>
                      <span style={{ color: c.bureau_score >= 750 ? "var(--green)" : c.bureau_score >= 700 ? "var(--text)" : "var(--amber)" }}>
                        {c.bureau_score}
                      </span>
                    </td>
                    <td>{card ? inr(card.current_limit) : "—"}</td>
                    <td style={{ minWidth: 160 }}>
                      {card ? (
                        <div className="row" style={{ gap: 8 }}>
                          <div className={`progress ${utilColor}`} style={{ flex: 1, maxWidth: 100 }}>
                            <div style={{ width: `${Math.min(util, 100)}%` }} />
                          </div>
                          <span className="muted" style={{ fontSize: 12, minWidth: 32 }}>{util.toFixed(0)}%</span>
                        </div>
                      ) : "—"}
                    </td>
                    <td><Pill variant={c.segment as "PREMIUM" | "MASS"} bare>{c.segment}</Pill></td>
                    <td>{card ? <Pill variant={card.benefits_tier as "GOLD" | "SILVER" | "PLATINUM"} bare>{card.benefits_tier}</Pill> : "—"}</td>
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

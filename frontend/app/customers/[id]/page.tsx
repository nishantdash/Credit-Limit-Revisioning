import Link from "next/link";
import { api, Card, Customer, Decision, inr, pct } from "../../../lib/api";
import { TriggerForm } from "./TriggerForm";

type Detail = {
  customer: Customer;
  card: Card | null;
  recent_transactions: {
    id: string; amount: number; merchant_category: string; merchant_tier: string; merchant_city: string; timestamp: string;
  }[];
  income_signals: { source: string; monthly_amount: number; as_of: string }[];
};

export default async function CustomerDetail({ params }: { params: { id: string } }) {
  const [detail, decisions] = await Promise.all([
    api<Detail>(`/customers/${params.id}`),
    api<Decision[]>(`/decisions/by-customer/${params.id}`),
  ]);
  const { customer, card, recent_transactions, income_signals } = detail;
  const utilisation = card && card.current_limit ? (card.current_balance / card.current_limit) * 100 : 0;

  return (
    <>
      <Link href="/customers" className="muted">← Customers</Link>
      <h2 style={{ marginTop: 8 }}>{customer.name} <span className={`badge badge-${customer.segment}`}>{customer.segment}</span></h2>
      <p className="page-sub">{customer.id} · {customer.programme_id} · {customer.employment_type}</p>

      <div className="grid cols-4">
        <Metric label="Current limit" value={card ? inr(card.current_limit) : "—"} />
        <Metric label="Current balance" value={card ? inr(card.current_balance) : "—"} sub={card ? `${utilisation.toFixed(1)}% utilisation` : undefined} />
        <Metric label="Benefits tier" value={card?.benefits_tier ?? "—"} />
        <Metric label="Bureau score" value={customer.bureau_score.toString()} sub={`DPD max 12m: ${customer.dpd_max_12m}`} />
      </div>

      <div className="divider" />

      <div className="grid cols-2">
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Income signals <span className="layer-badge">L1</span></h3>
          <table>
            <thead><tr><th>Source</th><th>Monthly</th><th>As of</th></tr></thead>
            <tbody>
              {income_signals.map((s, i) => (
                <tr key={i}>
                  <td>{s.source}</td>
                  <td>{inr(s.monthly_amount)}</td>
                  <td className="muted">{new Date(s.as_of).toLocaleDateString()}</td>
                </tr>
              ))}
              {income_signals.length === 0 && <tr><td colSpan={3} className="muted">No signals</td></tr>}
            </tbody>
          </table>
          <div className="metric-sub" style={{ marginTop: 8 }}>Stated at origination: {inr(customer.stated_income)}/mo</div>
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Recent transactions <span className="layer-badge">L1</span></h3>
          <table>
            <thead><tr><th>Date</th><th>Category</th><th>Tier</th><th>Amount</th></tr></thead>
            <tbody>
              {recent_transactions.slice(0, 8).map((t) => (
                <tr key={t.id}>
                  <td className="muted">{new Date(t.timestamp).toLocaleDateString()}</td>
                  <td>{t.merchant_category}</td>
                  <td>{t.merchant_tier === "PREMIUM" ? <span className="badge badge-PREMIUM">PREMIUM</span> : <span className="muted">{t.merchant_tier}</span>}</td>
                  <td>{inr(t.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="divider" />

      <h3 style={{ marginBottom: 12 }}>Decision history <span className="layer-badge">L3</span></h3>
      {decisions.length === 0 ? (
        <div className="card muted">No decisions yet. Fire a trigger below to generate one.</div>
      ) : (
        <div className="grid" style={{ gap: 12 }}>
          {decisions.map((d) => (
            <DecisionCard key={d.id} d={d} />
          ))}
        </div>
      )}

      <div className="divider" />

      <h3 style={{ marginBottom: 12 }}>Fire a trigger <span className="layer-badge">L3</span></h3>
      {card ? <TriggerForm cardId={card.id} /> : <div className="muted">No card on file</div>}
    </>
  );
}

function Metric({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="card">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      {sub && <div className="metric-sub">{sub}</div>}
    </div>
  );
}

function DecisionCard({ d }: { d: Decision }) {
  return (
    <div className="card">
      <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
        <div className="row" style={{ gap: 8 }}>
          <span className={`badge badge-${d.decision}`}>{d.decision}</span>
          <span className="muted">{d.id}</span>
          <span className="muted">· {d.trigger_type}</span>
        </div>
        <div className="row" style={{ gap: 8 }}>
          {d.hitl_required && <span className={`badge badge-${d.hitl_status}`}>HITL · {d.hitl_status}</span>}
          {d.executed && <span className="badge badge-APPROVED">EXECUTED</span>}
        </div>
      </div>
      <div className="row" style={{ gap: 24, marginBottom: 8 }}>
        <div>
          <div className="metric-label">Limit</div>
          <div>
            {d.decision === "FREEZE"
              ? inr(d.current_limit)
              : <>{inr(d.current_limit)} → <strong>{inr(d.recommended_limit)}</strong></>}
          </div>
        </div>
        <div>
          <div className="metric-label">PD pre → post</div>
          <div>{pct(d.pd_pre)} → {pct(d.pd_post_projected)}</div>
        </div>
        <div>
          <div className="metric-label">Income estimate</div>
          <div>{inr(d.income_estimate)}/mo</div>
        </div>
        <div>
          <div className="metric-label">Behavioral</div>
          <div>{d.behavioral_score.toFixed(0)}/100</div>
        </div>
        <div>
          <div className="metric-label">Confidence</div>
          <div>{(d.confidence * 100).toFixed(0)}%</div>
        </div>
        {d.benefits_tier_to && d.benefits_tier_to !== d.benefits_tier_from && (
          <div>
            <div className="metric-label">Tier</div>
            <div>
              <span className={`badge badge-${d.benefits_tier_from}`}>{d.benefits_tier_from}</span>
              {" → "}
              <span className={`badge badge-${d.benefits_tier_to}`}>{d.benefits_tier_to}</span>
            </div>
          </div>
        )}
      </div>
      <div className="reasons">
        {d.reason_codes.map((r) => <span key={r} className="reason-chip">{r}</span>)}
      </div>
      <div style={{ marginTop: 12 }}>
        <div className="metric-label">Officer note</div>
        <div style={{ marginTop: 4 }}>{d.explainer_text_officer}</div>
      </div>
      <div style={{ marginTop: 10 }}>
        <div className="metric-label">Customer copy</div>
        <div style={{ marginTop: 4 }} className="muted">{d.explainer_text_customer}</div>
      </div>
    </div>
  );
}

import Link from "next/link";
import { api, Card, Customer, Decision, inr, pct } from "../../../lib/api";
import { TriggerForm } from "./TriggerForm";
import { Avatar } from "../../../components/Avatar";
import { Icon } from "../../../components/Icon";
import { Pill } from "../../../components/Pill";

type Detail = {
  customer: Customer;
  card: Card | null;
  recent_transactions: { id: string; amount: number; merchant_category: string; merchant_tier: string; merchant_city: string; timestamp: string }[];
  income_signals: { source: string; monthly_amount: number; as_of: string }[];
};

export default async function CustomerDetail({ params }: { params: { id: string } }) {
  const [detail, decisions] = await Promise.all([
    api<Detail>(`/customers/${params.id}`),
    api<Decision[]>(`/decisions/by-customer/${params.id}`),
  ]);
  const { customer, card, recent_transactions, income_signals } = detail;
  const util = card?.current_limit ? (card.current_balance / card.current_limit) * 100 : 0;

  return (
    <>
      <Link href="/customers" className="row muted" style={{ marginBottom: 12, color: "var(--text-dim)", fontSize: 13, width: "fit-content" }}>
        <Icon name="arrow-right" size={14} className="muted" style={{ transform: "rotate(180deg)" }} />
        <span style={{ marginLeft: 6 }}>Back to customers</span>
      </Link>

      <div className="page-head">
        <div>
          <h2 className="page-title row" style={{ gap: 12 }}>
            {customer.name}
            <Pill variant={customer.dpd_max_12m > 0 ? "amber" : "green"}>{customer.dpd_max_12m > 0 ? "Watch" : "Active"}</Pill>
          </h2>
          <div className="page-sub row" style={{ gap: 6, marginBottom: 0 }}>
            <span>{customer.id}</span>
            <span>·</span>
            <span>{customer.programme_id}</span>
            <span>·</span>
            <span>{customer.employment_type === "SELF_EMPLOYED" ? "Self-employed" : "Salaried"}</span>
            <span>·</span>
            <Pill variant={customer.segment as "MASS" | "PREMIUM"} bare>{customer.segment}</Pill>
          </div>
        </div>
        <div className="actions">
          <button className="btn"><Icon name="shield" size={14} /> Freeze</button>
          <button className="btn"><Icon name="more" size={14} /> More</button>
        </div>
      </div>

      <div className="grid split-2-1">
        <div className="grid" style={{ gap: 16 }}>
          {card && <CardVisual card={card} customer={customer} util={util} />}

          <div className="card padless">
            <div className="card-head"><h3>Income signals <Pill variant="gray" bare>L1</Pill></h3>
              <span className="muted" style={{ fontSize: 12 }}>Stated at origination: {inr(customer.stated_income)}/mo</span>
            </div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Source</th><th>Monthly</th><th>As of</th></tr></thead>
                <tbody>
                  {income_signals.map((s, i) => (
                    <tr key={i}>
                      <td><span className="chip" style={{ background: "var(--primary-tint)", color: "var(--primary)", border: "none" }}>{s.source}</span></td>
                      <td><strong>{inr(s.monthly_amount)}</strong></td>
                      <td className="muted">{new Date(s.as_of).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}</td>
                    </tr>
                  ))}
                  {income_signals.length === 0 && <tr><td colSpan={3} className="empty">No income signals on file</td></tr>}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card padless">
            <div className="card-head"><h3>Recent transactions <Pill variant="gray" bare>L1</Pill></h3></div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Date</th><th>Category</th><th>Tier</th><th>City</th><th>Amount</th></tr></thead>
                <tbody>
                  {recent_transactions.slice(0, 8).map((t) => (
                    <tr key={t.id}>
                      <td className="muted">{new Date(t.timestamp).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}</td>
                      <td>{t.merchant_category}</td>
                      <td>{t.merchant_tier === "PREMIUM" ? <Pill variant="purple" bare>Premium</Pill> : <Pill variant="gray" bare>Standard</Pill>}</td>
                      <td className="muted">{t.merchant_city}</td>
                      <td><strong>{inr(t.amount)}</strong></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card padless">
            <div className="card-head">
              <h3>Decision history <Pill variant="gray" bare>L3</Pill></h3>
              <span className="muted" style={{ fontSize: 12 }}>{decisions.length} decisions</span>
            </div>
            <div className="card-body">
              {decisions.length === 0 ? (
                <div className="empty">No decisions yet. Fire a trigger to generate one.</div>
              ) : (
                <div className="grid" style={{ gap: 12 }}>
                  {decisions.map((d) => <DecisionRow key={d.id} d={d} />)}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="grid" style={{ gap: 16, alignContent: "start" }}>
          {card && (
            <div className="card">
              <h3 style={{ marginBottom: 16 }}>Account snapshot</h3>
              <div className="meta-row" style={{ flexDirection: "column", gap: 14 }}>
                <div className="meta-cell"><span className="lbl">Current limit</span><span className="val">{inr(card.current_limit)}</span></div>
                <div className="meta-cell">
                  <span className="lbl">Current balance · utilisation</span>
                  <span className="val">{inr(card.current_balance)} · {util.toFixed(1)}%</span>
                  <div className={`progress ${util > 80 ? "danger" : util > 60 ? "" : "success"}`} style={{ marginTop: 8 }}>
                    <div style={{ width: `${Math.min(util, 100)}%` }} />
                  </div>
                </div>
                <div className="meta-cell"><span className="lbl">Benefits tier</span><span className="val"><Pill variant={card.benefits_tier as "GOLD" | "SILVER" | "PLATINUM"} bare>{card.benefits_tier}</Pill></span></div>
                <div className="meta-cell"><span className="lbl">Bureau score</span><span className="val">{customer.bureau_score}</span></div>
                <div className="meta-cell"><span className="lbl">DPD max 12m</span><span className="val" style={{ color: customer.dpd_max_12m > 0 ? "var(--amber)" : "var(--text)" }}>{customer.dpd_max_12m}</span></div>
                <div className="meta-cell"><span className="lbl">Months at current limit</span><span className="val">{card.months_at_current_limit}</span></div>
              </div>
            </div>
          )}

          {card && (
            <div className="card">
              <h3 style={{ marginBottom: 4 }}>Fire a trigger <Pill variant="gray" bare>L3</Pill></h3>
              <p className="muted" style={{ fontSize: 12, marginTop: 0, marginBottom: 14 }}>Simulate an event to push this customer through a CLR review.</p>
              <TriggerForm cardId={card.id} />
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function CardVisual({ card, customer, util }: { card: Card; customer: Customer; util: number }) {
  const tierColor =
    card.benefits_tier === "PLATINUM" ? "linear-gradient(135deg, #475569, #1e293b)" :
    card.benefits_tier === "GOLD" ? "linear-gradient(135deg, #f59e0b, #d97706)" :
    "linear-gradient(135deg, #475569, #334155)";
  return (
    <div className="card padless" style={{ background: tierColor, color: "white", padding: 20, border: "none", boxShadow: "var(--shadow-md)" }}>
      <div className="row-between" style={{ alignItems: "flex-start", marginBottom: 32 }}>
        <div>
          <div style={{ fontSize: 11, opacity: 0.8, letterSpacing: 1, textTransform: "uppercase" }}>{customer.programme_id}</div>
          <div style={{ fontSize: 18, fontWeight: 600, marginTop: 4 }}>{customer.name}</div>
        </div>
        <div style={{ background: "rgba(255,255,255,0.15)", padding: "4px 10px", borderRadius: 999, fontSize: 11, fontWeight: 600, letterSpacing: 0.5 }}>
          {card.benefits_tier}
        </div>
      </div>
      <div style={{ fontFamily: "ui-monospace, Menlo, monospace", fontSize: 16, letterSpacing: 4, marginBottom: 12 }}>
        •••• •••• •••• {card.id.split("-").pop()}
      </div>
      <div className="row-between" style={{ alignItems: "flex-end" }}>
        <div>
          <div style={{ fontSize: 10, opacity: 0.75, letterSpacing: 0.5 }}>LIMIT · UTILISATION</div>
          <div style={{ fontSize: 16, fontWeight: 600, marginTop: 4 }}>{inr(card.current_limit)} · {util.toFixed(0)}%</div>
        </div>
        <div style={{ width: 36, height: 24, borderRadius: 4, background: "linear-gradient(135deg, #fbbf24, #f59e0b)" }} />
      </div>
    </div>
  );
}

function DecisionRow({ d }: { d: Decision }) {
  return (
    <div className="card flat" style={{ background: "var(--surface-2)" }}>
      <div className="row-between" style={{ marginBottom: 12 }}>
        <div className="row" style={{ gap: 10 }}>
          <Pill variant={d.decision}>{d.decision}</Pill>
          <span className="mono muted" style={{ fontSize: 11 }}>{d.id}</span>
          <span className="chip">{d.trigger_type}</span>
        </div>
        <div className="row" style={{ gap: 6 }}>
          {d.hitl_required && <Pill variant={d.hitl_status as "PENDING" | "APPROVED" | "REJECTED"}>HITL · {d.hitl_status}</Pill>}
          {d.executed && <Pill variant="EXECUTED">EXECUTED</Pill>}
        </div>
      </div>
      <div className="meta-row" style={{ marginBottom: 12 }}>
        <div className="meta-cell">
          <span className="lbl">Limit</span>
          <span className="val">
            {d.decision === "FREEZE"
              ? inr(d.current_limit)
              : <>{inr(d.current_limit)} <Icon name="arrow-right" size={12} /> <strong>{inr(d.recommended_limit)}</strong></>}
          </span>
        </div>
        <div className="meta-cell"><span className="lbl">PD pre → post</span><span className="val">{pct(d.pd_pre)} → {pct(d.pd_post_projected)}</span></div>
        <div className="meta-cell"><span className="lbl">Income est.</span><span className="val">{inr(d.income_estimate)}/mo</span></div>
        <div className="meta-cell"><span className="lbl">Behavioral</span><span className="val">{d.behavioral_score.toFixed(0)}/100</span></div>
        <div className="meta-cell">
          <span className="lbl">Confidence</span>
          <span className="val row" style={{ gap: 6 }}>
            {(d.confidence * 100).toFixed(0)}%
            <span className="conf-bar"><span style={{ display: "block", width: `${d.confidence * 100}%`, height: "100%", background: "linear-gradient(to right, var(--amber), var(--green))" }} /></span>
          </span>
        </div>
        {d.benefits_tier_to && d.benefits_tier_to !== d.benefits_tier_from && (
          <div className="meta-cell">
            <span className="lbl">Tier change</span>
            <span className="val row" style={{ gap: 4 }}>
              <Pill variant={d.benefits_tier_from as "SILVER" | "GOLD" | "PLATINUM"} bare>{d.benefits_tier_from}</Pill>
              <Icon name="arrow-right" size={12} />
              <Pill variant={d.benefits_tier_to as "SILVER" | "GOLD" | "PLATINUM"} bare>{d.benefits_tier_to}</Pill>
            </span>
          </div>
        )}
      </div>
      <div className="reasons" style={{ marginBottom: 10 }}>
        {d.reason_codes.map((r) => <span key={r} className="chip">{r}</span>)}
      </div>
      <div style={{ fontSize: 13, color: "var(--text-2)", borderTop: "1px solid var(--border)", paddingTop: 10 }}>
        <div className="muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 4 }}>Officer note</div>
        {d.explainer_text_officer}
      </div>
      <div style={{ marginTop: 8, fontSize: 13 }}>
        <div className="muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 4 }}>Customer copy</div>
        <span className="muted">{d.explainer_text_customer}</span>
      </div>
    </div>
  );
}

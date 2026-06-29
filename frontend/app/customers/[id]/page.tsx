import Link from "next/link";
import {
  api, Card, Customer, Decision, inr, pct, TIER_LABEL,
  DIRECTION_VARIANT, INTENT_VARIANT,
} from "../../../lib/api";
import { TriggerForm } from "./TriggerForm";
import { Avatar } from "../../../components/Avatar";
import { Icon } from "../../../components/Icon";
import { Pill } from "../../../components/Pill";

type Txn = { id: string; amount: number; category_class: string; merchant_category: string; is_recurring: boolean; is_declined: boolean; merchant_city: string; timestamp: string };
type Sig = { source: string; monthly_amount: number; regularity: number; as_of: string };
type Detail = {
  customer: Customer; card: Card | null; latest_tier: number | null; latest_intent: string | null;
  recent_transactions: Txn[]; cashflow_signals: Sig[];
};

const LAYER_TITLES: Record<string, { n: string; t: string }> = {
  layer1_repayment: { n: "1", t: "Repayment & credit history" },
  layer2_behavioural: { n: "2", t: "Behavioural & transactional intent" },
  layer3_stability: { n: "3", t: "Stability & fulfilment (AA rail)" },
  layer4_network: { n: "4", t: "Network (positive-only)" },
  layer5_liquidity: { n: "5", t: "Real-time context & liquidity" },
};

function fmtVal(v: unknown): string {
  if (typeof v === "boolean") return v ? "yes" : "no";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : v.toFixed(3);
  if (Array.isArray(v)) return v.join(", ") || "—";
  if (v && typeof v === "object") return Object.entries(v).map(([k, x]) => `${k} ${typeof x === "number" ? (x as number).toFixed(2) : x}`).join(" · ");
  return String(v ?? "—");
}

export default async function CustomerDetail({ params }: { params: { id: string } }) {
  const [detail, decisions] = await Promise.all([
    api<Detail>(`/customers/${params.id}`),
    api<Decision[]>(`/decisions/by-customer/${params.id}`),
  ]);
  const { customer, card, recent_transactions, cashflow_signals } = detail;
  const util = card?.current_limit ? (card.outstanding / card.current_limit) * 100 : 0;
  const latest = decisions[0];
  const snapshot = latest?.signal_snapshot ?? {};

  const flags: { label: string; variant: string }[] = [];
  if (customer.fraud_flag) flags.push({ label: "Fraud flag", variant: "red" });
  if (customer.legal_block_flag) flags.push({ label: "Legal block", variant: "red" });
  if (customer.dpd_max_12m >= 30) flags.push({ label: `${customer.dpd_max_12m} DPD`, variant: "red" });
  else if (customer.dpd_max_12m > 0) flags.push({ label: `${customer.dpd_max_12m} DPD`, variant: "amber" });
  if (!customer.aa_consent_active) flags.push({ label: "No AA consent", variant: "amber" });

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
            <Pill variant={customer.entity_type}>{customer.entity_type}</Pill>
            {detail.latest_tier && <Pill variant={`tier${detail.latest_tier}`}>{TIER_LABEL[detail.latest_tier]}</Pill>}
            {detail.latest_intent && <Pill variant={INTENT_VARIANT[detail.latest_intent]}>{detail.latest_intent}</Pill>}
          </h2>
          <div className="page-sub row" style={{ gap: 6, marginBottom: 0, flexWrap: "wrap" }}>
            <span>{customer.id}</span><span>·</span><span>{customer.programme_id}</span><span>·</span>
            <span>{customer.employment_type.replace("_", "-").toLowerCase()}</span>
            {flags.map((f) => <Pill key={f.label} variant={f.variant} bare>{f.label}</Pill>)}
          </div>
        </div>
      </div>

      <div className="grid split-2-1">
        <div className="grid" style={{ gap: 16 }}>
          {latest && <DecisionHero d={latest} />}

          {Object.keys(snapshot).length > 0 && (
            <div className="card padless">
              <div className="card-head"><h3>Five signal layers</h3><span className="muted" style={{ fontSize: 12 }}>from latest decision</span></div>
              <div style={{ padding: 14 }}>
                {Object.entries(LAYER_TITLES).map(([key, meta]) => {
                  const layer = snapshot[key] as Record<string, unknown> | undefined;
                  if (!layer) return null;
                  return (
                    <div className="layer" key={key}>
                      <div className="layer-head"><span className="lnum">{meta.n}</span><span className="ltitle">{meta.t}</span></div>
                      <div className="layer-body">
                        {Object.entries(layer).map(([k, v]) => (
                          <div className="layer-kv" key={k}><span className="k">{k.replace(/_/g, " ")}</span><span className="v">{fmtVal(v)}</span></div>
                        ))}
                      </div>
                    </div>
                  );
                })}
                {snapshot["msme_double_gate"] && (
                  <div className="layer">
                    <div className="layer-head"><span className="lnum" style={{ background: "var(--teal-tint)", color: "var(--teal)" }}>M</span><span className="ltitle">MSME double-gate</span></div>
                    <div className="layer-body">
                      {Object.entries(snapshot["msme_double_gate"] as Record<string, unknown>).map(([k, v]) => (
                        <div className="layer-kv" key={k}><span className="k">{k.replace(/_/g, " ")}</span><span className="v">{fmtVal(v)}</span></div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="card padless">
            <div className="card-head"><h3>Cashflow signals <Pill variant="gray" bare>L3 · AA</Pill></h3>
              <span className="muted" style={{ fontSize: 12 }}>stated: {inr(customer.stated_income)}/mo</span></div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Source</th><th>Monthly</th><th>Regularity</th><th>As of</th></tr></thead>
                <tbody>
                  {cashflow_signals.map((s, i) => (
                    <tr key={i}>
                      <td><span className="chip" style={{ background: "var(--primary-tint)", color: "var(--primary)", border: "none" }}>{s.source}</span></td>
                      <td><strong>{inr(s.monthly_amount)}</strong></td>
                      <td>
                        <div className="row" style={{ gap: 8 }}>
                          <div className={`progress ${s.regularity > 0.7 ? "success" : s.regularity < 0.5 ? "danger" : ""}`} style={{ flex: 1, maxWidth: 80 }}><div style={{ width: `${s.regularity * 100}%` }} /></div>
                          <span className="muted" style={{ fontSize: 12 }}>{(s.regularity * 100).toFixed(0)}%</span>
                        </div>
                      </td>
                      <td className="muted">{new Date(s.as_of).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}</td>
                    </tr>
                  ))}
                  {cashflow_signals.length === 0 && <tr><td colSpan={4} className="empty">No cashflow signals</td></tr>}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card padless">
            <div className="card-head"><h3>Recent transactions <Pill variant="gray" bare>L2</Pill></h3></div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Date</th><th>Category</th><th>Class</th><th>City</th><th>Amount</th></tr></thead>
                <tbody>
                  {recent_transactions.slice(0, 8).map((t) => (
                    <tr key={t.id}>
                      <td className="muted">{new Date(t.timestamp).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}</td>
                      <td>{t.merchant_category}{t.is_recurring && <span style={{ marginLeft: 6 }}><Pill variant="gray" bare>recurring</Pill></span>}{t.is_declined && <span style={{ marginLeft: 6 }}><Pill variant="red" bare>declined</Pill></span>}</td>
                      <td><Pill variant={t.category_class === "ASPIRATIONAL" ? "purple" : t.category_class === "DISCRETIONARY" ? "blue" : "gray"} bare>{t.category_class.slice(0, 4)}</Pill></td>
                      <td className="muted">{t.merchant_city}</td>
                      <td><strong>{inr(t.amount)}</strong></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card padless">
            <div className="card-head"><h3>Decision history</h3><span className="muted" style={{ fontSize: 12 }}>{decisions.length} decisions</span></div>
            <div className="card-body">
              {decisions.length === 0 ? <div className="empty">No decisions yet. Fire a trigger to generate one.</div> : (
                <div className="grid" style={{ gap: 12 }}>{decisions.map((d) => <DecisionRow key={d.id} d={d} />)}</div>
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
                  <span className="lbl">Outstanding · utilisation</span>
                  <span className="val">{inr(card.outstanding)} · {util.toFixed(1)}%</span>
                  <div className={`progress ${util > 80 ? "danger" : util > 60 ? "" : "success"}`} style={{ marginTop: 8 }}><div style={{ width: `${Math.min(util, 100)}%` }} /></div>
                </div>
                <div className="meta-cell"><span className="lbl">Bureau score</span><span className="val">{customer.bureau_score}</span></div>
                <div className="meta-cell"><span className="lbl">Account vintage</span><span className="val">{customer.account_vintage_months} months</span></div>
                <div className="meta-cell"><span className="lbl">Months since last change</span><span className="val">{card.months_since_last_change}</span></div>
                <div className="meta-cell"><span className="lbl">Peak drawn (12m)</span><span className="val">{inr(card.peak_drawn_12m)}</span></div>
                {customer.entity_type === "MSME" && (
                  <>
                    <div className="meta-cell"><span className="lbl">Trade-credit DPD</span><span className="val" style={{ color: (customer.trade_dpd_days ?? 0) > 0 ? "var(--red)" : "var(--text)" }}>{customer.trade_dpd_days ?? 0} days</span></div>
                    <div className="meta-cell"><span className="lbl">DSCR · WC utilisation</span><span className="val">{customer.dscr?.toFixed(2)} · {((customer.working_capital_utilization ?? 0) * 100).toFixed(0)}%</span></div>
                  </>
                )}
              </div>
            </div>
          )}

          {card && (
            <div className="card">
              <h3 style={{ marginBottom: 4 }}>Fire a trigger <Pill variant="gray" bare>L1</Pill></h3>
              <p className="muted" style={{ fontSize: 12, marginTop: 0, marginBottom: 14 }}>Simulate an AA/event trigger to push this customer through a CLR review.</p>
              <TriggerForm cardId={card.id} />
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function DecisionHero({ d }: { d: Decision }) {
  const grad = d.direction === "INCREASE" ? "linear-gradient(135deg, #16a34a, #15803d)" : d.direction === "DECREASE" ? "linear-gradient(135deg, #dc2626, #b91c1c)" : "linear-gradient(135deg, #475569, #334155)";
  return (
    <div className="card padless" style={{ background: grad, color: "white", padding: 20, border: "none", boxShadow: "var(--shadow-md)" }}>
      <div className="row-between" style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 12, opacity: 0.85, letterSpacing: 0.5, textTransform: "uppercase" }}>{d.matrix_cell}</div>
        <div style={{ background: "rgba(255,255,255,0.18)", padding: "3px 10px", borderRadius: 999, fontSize: 11, fontWeight: 600 }}>{d.intent}</div>
      </div>
      <div className="row" style={{ gap: 24, flexWrap: "wrap" }}>
        <Four label="Direction" value={d.direction} />
        <Four label="Magnitude" value={d.direction === "MAINTAIN" || d.direction === "FREEZE" ? "—" : `${d.magnitude_pct > 0 ? "+" : ""}${d.magnitude_pct.toFixed(1)}%`} />
        <Four label="Duration" value={d.duration} />
        <Four label="Confidence" value={`${(d.confidence * 100).toFixed(0)}%`} />
      </div>
      {d.direction !== "MAINTAIN" && d.direction !== "FREEZE" && (
        <div style={{ marginTop: 16, fontSize: 16, fontWeight: 600 }}>{inr(d.current_limit)} → {inr(d.recommended_limit)}</div>
      )}
      <div style={{ marginTop: 6, fontSize: 12, opacity: 0.85 }}>
        {d.pipeline === "OFFER" ? "Offer pipeline · consent-gated" : d.pipeline === "ACTION" ? "Action pipeline · applied with buffer" : "No change"}
        {d.auto_revert_at && ` · reverts ${new Date(d.auto_revert_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}`}
      </div>
    </div>
  );
}

function Four({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ fontSize: 10, opacity: 0.75, letterSpacing: 0.5, textTransform: "uppercase" }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 700, marginTop: 2 }}>{value}</div>
    </div>
  );
}

function DecisionRow({ d }: { d: Decision }) {
  return (
    <div className="card flat" style={{ background: "var(--surface-2)" }}>
      <div className="row-between" style={{ marginBottom: 12 }}>
        <div className="row" style={{ gap: 10 }}>
          <Pill variant={DIRECTION_VARIANT[d.direction]}>{d.direction}</Pill>
          <Pill variant={INTENT_VARIANT[d.intent]} bare>{d.intent}</Pill>
          <span className="mono muted" style={{ fontSize: 11 }}>{d.id}</span>
          <span className="chip">{d.trigger_type}</span>
        </div>
        <div className="row" style={{ gap: 6 }}>
          {d.pipeline === "OFFER" && <Pill variant={d.consent_status === "ACCEPTED" ? "ACCEPTED" : "PENDING_CONSENT"}>{d.consent_status === "ACCEPTED" ? "consent ✓" : "awaiting consent"}</Pill>}
          {d.pipeline === "ACTION" && d.executed && <Pill variant="ACCEPTED" bare>applied</Pill>}
          {d.review_status === "PENDING" && <Pill variant="amber">review</Pill>}
        </div>
      </div>
      <div className="meta-row" style={{ marginBottom: 12 }}>
        <div className="meta-cell"><span className="lbl">Limit</span><span className="val">{d.direction === "MAINTAIN" || d.direction === "FREEZE" ? inr(d.current_limit) : <>{inr(d.current_limit)} → <strong>{inr(d.recommended_limit)}</strong></>}</span></div>
        <div className="meta-cell"><span className="lbl">Magnitude · duration</span><span className="val">{d.magnitude_pct.toFixed(1)}% · {d.duration}</span></div>
        <div className="meta-cell"><span className="lbl">PD pre → post</span><span className="val">{pct(d.pd_pre)} → {pct(d.pd_post_projected)}</span></div>
        <div className="meta-cell"><span className="lbl">Confidence</span><span className="val">{(d.confidence * 100).toFixed(0)}%</span></div>
      </div>
      <div className="reasons" style={{ marginBottom: 10 }}>
        {d.reason_codes.map((r) => <span key={r} className="chip">{r}</span>)}
        {d.applied_caps.map((r) => <span key={r} className="chip" style={{ borderColor: "var(--amber)", color: "var(--amber)" }}>{r}</span>)}
      </div>
      <div style={{ fontSize: 13, color: "var(--text-2)", borderTop: "1px solid var(--border)", paddingTop: 10 }}>
        <div className="muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 4 }}>Officer note</div>
        {d.explainer_officer}
      </div>
    </div>
  );
}

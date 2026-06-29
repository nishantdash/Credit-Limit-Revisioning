"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, Customer, Decision, inr, DIRECTION_VARIANT, INTENT_VARIANT } from "../../lib/api";
import { Avatar } from "../../components/Avatar";
import { Icon } from "../../components/Icon";
import { Pill } from "../../components/Pill";

type EventDef = { value: string; label: string; description: string; color: "blue" | "purple" | "green" | "amber"; icon: Parameters<typeof Icon>[0]["name"] };

const EVENT_TYPES: EventDef[] = [
  { value: "SALARY_CREDIT", label: "Salary credit", description: "An AA-detected salary inflow — a live stability + capacity signal.", color: "green", icon: "trend-up" },
  { value: "UTILIZATION_THRESHOLD", label: "Utilisation threshold", description: "Utilisation crosses a configured band. Fires an immediate review.", color: "blue", icon: "spark" },
  { value: "DECLINED_HIGH_VALUE_TXN", label: "Declined high-value txn", description: "A high-value decline against the limit — strong real-time demand signal.", color: "amber", icon: "alert-circle" },
];

const COLOR_BG: Record<EventDef["color"], string> = { blue: "var(--primary-tint)", purple: "var(--purple-tint)", green: "var(--green-tint)", amber: "var(--amber-tint)" };
const COLOR_FG: Record<EventDef["color"], string> = { blue: "var(--primary)", purple: "var(--purple)", green: "var(--green)", amber: "var(--amber)" };

export function TriggerSimulator({ customers }: { customers: Customer[] }) {
  const router = useRouter();
  const [customerId, setCustomerId] = useState(customers[0]?.id ?? "");
  const [event, setEvent] = useState(EVENT_TYPES[0].value);
  const [busy, setBusy] = useState(false);
  const [single, setSingle] = useState<Decision | null>(null);
  const [sweep, setSweep] = useState<Decision[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function fire() {
    setBusy(true); setError(null); setSingle(null); setSweep(null);
    try {
      const cardId = `CARD-${customerId.split("-").pop()}`;
      const dec = await api<Decision>("/triggers/fire", { method: "POST", body: JSON.stringify({ card_id: cardId, event_type: event, payload: {} }) });
      setSingle(dec);
      router.refresh();
    } catch (e: unknown) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }

  async function runSweep() {
    setBusy(true); setError(null); setSingle(null); setSweep(null);
    try {
      const decisions = await api<Decision[]>("/triggers/micro-review-sweep", { method: "POST" });
      setSweep(decisions);
      router.refresh();
    } catch (e: unknown) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }

  return (
    <>
      <div className="grid cols-3" style={{ marginBottom: 16 }}>
        {EVENT_TYPES.map((e) => (
          <button key={e.value} onClick={() => setEvent(e.value)} className="card"
            style={{ textAlign: "left", cursor: "pointer", border: event === e.value ? "1px solid var(--primary)" : undefined, boxShadow: event === e.value ? "0 0 0 3px rgba(47, 85, 236, 0.12)" : undefined, background: "var(--surface)", padding: 18 }}>
            <div className="row-between" style={{ marginBottom: 12 }}>
              <div style={{ width: 36, height: 36, borderRadius: 10, background: COLOR_BG[e.color], color: COLOR_FG[e.color], display: "grid", placeItems: "center" }}><Icon name={e.icon} size={18} /></div>
              {event === e.value && <Pill variant="blue" bare>Selected</Pill>}
            </div>
            <div style={{ fontWeight: 600, color: "var(--text)", marginBottom: 4 }}>{e.label}</div>
            <div style={{ fontSize: 12, color: "var(--text-dim)", lineHeight: 1.5 }}>{e.description}</div>
          </button>
        ))}
      </div>

      <div className="card">
        <h3 style={{ marginBottom: 14 }}>Fire on a single customer</h3>
        <div className="grid cols-3" style={{ alignItems: "end" }}>
          <div>
            <label className="muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.4 }}>Customer</label>
            <select value={customerId} onChange={(e) => setCustomerId(e.target.value)} style={{ marginTop: 4 }}>
              {customers.map((c) => <option key={c.id} value={c.id}>{c.id} — {c.name}</option>)}
            </select>
          </div>
          <div>
            <label className="muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.4 }}>Event</label>
            <select value={event} onChange={(e) => setEvent(e.target.value)} style={{ marginTop: 4 }}>
              {EVENT_TYPES.map((e) => <option key={e.value} value={e.value}>{e.label}</option>)}
            </select>
          </div>
          <button className="btn btn-primary" onClick={fire} disabled={busy}><Icon name="play" size={14} /> {busy ? "Firing…" : "Fire event"}</button>
        </div>
        <div className="card-divider" />
        <div className="row-between">
          <div>
            <div style={{ fontWeight: 600 }}>Micro-review sweep</div>
            <div className="muted" style={{ fontSize: 12 }}>Continuous re-scoring across all {customers.length} customers — replaces the quarterly batch.</div>
          </div>
          <button className="btn" onClick={runSweep} disabled={busy}><Icon name="bolt" size={14} /> Run full sweep</button>
        </div>
        {error && <div style={{ color: "var(--red)", marginTop: 12, fontSize: 13 }}>{error}</div>}
      </div>

      {single && (
        <div className="card" style={{ marginTop: 16 }}>
          <div className="row" style={{ gap: 10, marginBottom: 10, flexWrap: "wrap" }}>
            <Pill variant={DIRECTION_VARIANT[single.direction]}>{single.direction}</Pill>
            <Pill variant={INTENT_VARIANT[single.intent]} bare>{single.intent}</Pill>
            <span className="muted" style={{ fontSize: 12 }}>{single.matrix_cell}</span>
            {single.pipeline !== "NONE" && <Pill variant={single.pipeline} bare>{single.pipeline}</Pill>}
            {single.review_required && <Pill variant="amber">review</Pill>}
          </div>
          <div style={{ fontSize: 13 }}>{single.explainer_officer}</div>
        </div>
      )}

      {sweep && (
        <div className="card padless" style={{ marginTop: 16 }}>
          <div className="card-head"><h3>Sweep results · {sweep.length} decisions</h3></div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Intent</th><th>Customer</th><th>Cell</th><th>Decision</th><th>Pipeline</th></tr></thead>
              <tbody>
                {sweep.map((d) => (
                  <tr key={d.id}>
                    <td><Pill variant={INTENT_VARIANT[d.intent]} bare>{d.intent}</Pill></td>
                    <td><div className="row" style={{ gap: 10 }}><Avatar id={d.customer_id} size="sm" /><Link href={`/customers/${d.customer_id}`} style={{ color: "var(--text)" }}>{d.customer_id}</Link></div></td>
                    <td className="muted" style={{ fontSize: 12 }}>{d.matrix_cell}</td>
                    <td>
                      <Pill variant={DIRECTION_VARIANT[d.direction]}>{d.direction}</Pill>{" "}
                      {d.direction !== "MAINTAIN" && d.direction !== "FREEZE" && <span className="muted" style={{ fontSize: 12 }}>{inr(d.current_limit)}→{inr(d.recommended_limit)}</span>}
                    </td>
                    <td>{d.pipeline === "NONE" ? <span className="muted">—</span> : <Pill variant={d.pipeline} bare>{d.pipeline}</Pill>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  );
}

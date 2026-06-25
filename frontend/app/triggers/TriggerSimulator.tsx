"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, Customer, Decision, inr } from "../../lib/api";
import { Avatar } from "../../components/Avatar";
import { Icon } from "../../components/Icon";
import { Pill } from "../../components/Pill";

type EventDef = {
  value: string;
  label: string;
  description: string;
  color: "blue" | "purple" | "green" | "amber";
  icon: Parameters<typeof Icon>[0]["name"];
};

const EVENT_TYPES: EventDef[] = [
  { value: "CARD_UTILIZATION_THRESHOLD", label: "Utilisation threshold", description: "Customer hits 80%+ utilisation. Fires an immediate review.", color: "blue", icon: "trend-up" },
  { value: "SPEND_SPIKE_DETECTED", label: "Spend spike", description: "30-day spend jumps >50% over prior 30-day window.", color: "purple", icon: "spark" },
  { value: "INCOME_STEPCHANGE", label: "Income step-change", description: "Live cashflow estimator detects a salary credit ≥30% above 6-mo avg.", color: "green", icon: "trend-up" },
  { value: "PERIODIC_SWEEP", label: "Periodic sweep", description: "Monthly batch over the whole eligible cohort.", color: "amber", icon: "calendar" },
];

const COLOR_BG: Record<EventDef["color"], string> = {
  blue: "var(--primary-tint)",
  purple: "var(--purple-tint)",
  green: "var(--green-tint)",
  amber: "var(--amber-tint)",
};
const COLOR_FG: Record<EventDef["color"], string> = {
  blue: "var(--primary)",
  purple: "var(--purple)",
  green: "var(--green)",
  amber: "var(--amber)",
};

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
      const dec = await api<Decision>("/triggers/fire", {
        method: "POST",
        body: JSON.stringify({ card_id: cardId, event_type: event, payload: {} }),
      });
      setSingle(dec);
      router.refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally { setBusy(false); }
  }

  async function runSweep() {
    setBusy(true); setError(null); setSingle(null); setSweep(null);
    try {
      const decisions = await api<Decision[]>("/triggers/periodic-sweep", { method: "POST" });
      setSweep(decisions);
      router.refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally { setBusy(false); }
  }

  return (
    <>
      <div className="grid cols-3" style={{ marginBottom: 16 }}>
        {EVENT_TYPES.slice(0, 3).map((e) => (
          <button
            key={e.value}
            onClick={() => setEvent(e.value)}
            className="card"
            style={{
              textAlign: "left",
              cursor: "pointer",
              border: event === e.value ? "1px solid var(--primary)" : undefined,
              boxShadow: event === e.value ? "0 0 0 3px rgba(47, 85, 236, 0.12)" : undefined,
              background: "var(--surface)",
              padding: 18,
            }}
          >
            <div className="row-between" style={{ marginBottom: 12 }}>
              <div style={{ width: 36, height: 36, borderRadius: 10, background: COLOR_BG[e.color], color: COLOR_FG[e.color], display: "grid", placeItems: "center" }}>
                <Icon name={e.icon} size={18} />
              </div>
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
          <button className="btn btn-primary" onClick={fire} disabled={busy}>
            <Icon name="play" size={14} /> {busy ? "Firing…" : "Fire event"}
          </button>
        </div>
        <div className="card-divider" />
        <div className="row-between">
          <div>
            <div style={{ fontWeight: 600 }}>Periodic sweep</div>
            <div className="muted" style={{ fontSize: 12 }}>Runs the L3 engine on every one of the {customers.length} eligible customers.</div>
          </div>
          <button className="btn" onClick={runSweep} disabled={busy}>
            <Icon name="bolt" size={14} /> Run full sweep
          </button>
        </div>
        {error && <div style={{ color: "var(--red)", marginTop: 12, fontSize: 13 }}>{error}</div>}
      </div>

      {single && (
        <div className="card" style={{ marginTop: 16 }}>
          <div className="row" style={{ gap: 10, marginBottom: 10 }}>
            <Pill variant={single.decision}>{single.decision}</Pill>
            <span className="mono muted" style={{ fontSize: 12 }}>{single.id}</span>
            {single.hitl_required && <Pill variant={single.hitl_status as "PENDING"}>HITL · {single.hitl_status}</Pill>}
            {single.executed && <Pill variant="EXECUTED">EXECUTED</Pill>}
          </div>
          <div style={{ fontSize: 13 }}>{single.explainer_text_officer}</div>
        </div>
      )}

      {sweep && (
        <div className="card padless" style={{ marginTop: 16 }}>
          <div className="card-head"><h3>Sweep results · {sweep.length} decisions</h3></div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Decision</th><th>Customer</th><th>Limit change</th><th>HITL</th><th>Executed</th></tr></thead>
              <tbody>
                {sweep.map((d) => (
                  <tr key={d.id}>
                    <td><Pill variant={d.decision}>{d.decision}</Pill></td>
                    <td>
                      <div className="row" style={{ gap: 10 }}>
                        <Avatar id={d.customer_id} size="sm" />
                        <Link href={`/customers/${d.customer_id}`} style={{ color: "var(--text)" }}>{d.customer_id}</Link>
                      </div>
                    </td>
                    <td>
                      {d.decision === "FREEZE"
                        ? <span className="muted">{inr(d.current_limit)}</span>
                        : <>{inr(d.current_limit)} <Icon name="arrow-right" size={12} /> {inr(d.recommended_limit)}</>}
                    </td>
                    <td>{d.hitl_required ? <Pill variant={d.hitl_status as "PENDING"}>{d.hitl_status}</Pill> : <span className="muted">—</span>}</td>
                    <td>{d.executed ? <Icon name="check" size={14} className="muted" /> : <span className="muted">—</span>}</td>
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

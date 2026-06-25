"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, Customer, Decision, inr } from "../../lib/api";

const EVENT_TYPES = [
  { value: "CARD_UTILIZATION_THRESHOLD", label: "Utilisation threshold (>80%)" },
  { value: "SPEND_SPIKE_DETECTED", label: "Spend spike detected" },
  { value: "INCOME_STEPCHANGE", label: "Income step-change" },
  { value: "PERIODIC_SWEEP", label: "Periodic sweep (single customer)" },
];

export function TriggerSimulator({ customers }: { customers: Customer[] }) {
  const router = useRouter();
  const [customerId, setCustomerId] = useState(customers[0]?.id ?? "");
  const [event, setEvent] = useState(EVENT_TYPES[0].value);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Decision | null>(null);
  const [sweep, setSweep] = useState<Decision[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function fire() {
    setBusy(true); setError(null); setResult(null); setSweep(null);
    try {
      const cardId = `CARD-${customerId.split("-").pop()}`;
      const dec = await api<Decision>("/triggers/fire", {
        method: "POST",
        body: JSON.stringify({ card_id: cardId, event_type: event, payload: {} }),
      });
      setResult(dec);
      router.refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function runSweep() {
    setBusy(true); setError(null); setResult(null); setSweep(null);
    try {
      const decisions = await api<Decision[]>("/triggers/periodic-sweep", { method: "POST" });
      setSweep(decisions);
      router.refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="card">
        <div className="grid cols-2">
          <div>
            <label className="metric-label">Customer</label>
            <select value={customerId} onChange={(e) => setCustomerId(e.target.value)} style={{ marginTop: 4 }}>
              {customers.map((c) => <option key={c.id} value={c.id}>{c.id} — {c.name}</option>)}
            </select>
          </div>
          <div>
            <label className="metric-label">Event</label>
            <select value={event} onChange={(e) => setEvent(e.target.value)} style={{ marginTop: 4 }}>
              {EVENT_TYPES.map((e) => <option key={e.value} value={e.value}>{e.label}</option>)}
            </select>
          </div>
        </div>
        <div className="row" style={{ gap: 12, marginTop: 16 }}>
          <button className="btn btn-primary" onClick={fire} disabled={busy || !customerId}>
            {busy ? "Firing…" : "Fire single event"}
          </button>
          <button className="btn" onClick={runSweep} disabled={busy}>
            Run periodic sweep on all {customers.length} customers
          </button>
        </div>
        {error && <div className="metric-sub" style={{ color: "var(--red)", marginTop: 12 }}>{error}</div>}
      </div>

      {result && (
        <>
          <div style={{ height: 16 }} />
          <div className="card">
            <div className="row" style={{ gap: 8, marginBottom: 8 }}>
              <span className={`badge badge-${result.decision}`}>{result.decision}</span>
              <strong>{result.id}</strong>
              {result.hitl_required && <span className={`badge badge-${result.hitl_status}`}>HITL · {result.hitl_status}</span>}
              {result.executed && <span className="badge badge-APPROVED">EXECUTED</span>}
            </div>
            <div>{result.explainer_text_officer}</div>
          </div>
        </>
      )}

      {sweep && (
        <>
          <div style={{ height: 16 }} />
          <div className="card" style={{ padding: 0 }}>
            <table>
              <thead>
                <tr><th>Decision</th><th>Customer</th><th>Limit change</th><th>HITL</th><th>Executed</th></tr>
              </thead>
              <tbody>
                {sweep.map((d) => (
                  <tr key={d.id}>
                    <td><span className={`badge badge-${d.decision}`}>{d.decision}</span></td>
                    <td>{d.customer_id}</td>
                    <td>
                      {d.decision === "FREEZE"
                        ? <span className="muted">{inr(d.current_limit)}</span>
                        : <>{inr(d.current_limit)} → {inr(d.recommended_limit)}</>}
                    </td>
                    <td><span className={`badge badge-${d.hitl_status}`}>{d.hitl_status}</span></td>
                    <td>{d.executed ? "✓" : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}

"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, Decision } from "../../../lib/api";

const EVENT_TYPES = [
  { value: "CARD_UTILIZATION_THRESHOLD", label: "Utilisation threshold (>80%)" },
  { value: "SPEND_SPIKE_DETECTED", label: "Spend spike detected" },
  { value: "INCOME_STEPCHANGE", label: "Income step-change" },
  { value: "PERIODIC_SWEEP", label: "Periodic sweep" },
];

export function TriggerForm({ cardId }: { cardId: string }) {
  const router = useRouter();
  const [event, setEvent] = useState(EVENT_TYPES[0].value);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Decision | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function fire() {
    setLoading(true);
    setError(null);
    try {
      const dec = await api<Decision>("/triggers/fire", {
        method: "POST",
        body: JSON.stringify({ card_id: cardId, event_type: event, payload: {} }),
      });
      setResult(dec);
      router.refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <div className="row" style={{ gap: 12 }}>
        <select value={event} onChange={(e) => setEvent(e.target.value)} style={{ maxWidth: 320 }}>
          {EVENT_TYPES.map((e) => <option key={e.value} value={e.value}>{e.label}</option>)}
        </select>
        <button className="btn btn-primary" onClick={fire} disabled={loading}>
          {loading ? "Firing…" : "Fire event"}
        </button>
      </div>
      {result && (
        <div className="metric-sub" style={{ marginTop: 12 }}>
          Decision <strong>{result.id}</strong> — <span className={`badge badge-${result.decision}`}>{result.decision}</span>
          {result.hitl_required ? " — sent to HITL queue" : " — auto-executed"}
        </div>
      )}
      {error && <div className="metric-sub" style={{ color: "var(--red)", marginTop: 12 }}>{error}</div>}
    </div>
  );
}

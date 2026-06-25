"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, Decision } from "../../../lib/api";
import { Icon } from "../../../components/Icon";
import { Pill } from "../../../components/Pill";

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
    <>
      <select value={event} onChange={(e) => setEvent(e.target.value)} style={{ marginBottom: 10 }}>
        {EVENT_TYPES.map((e) => <option key={e.value} value={e.value}>{e.label}</option>)}
      </select>
      <button className="btn btn-primary" style={{ width: "100%" }} onClick={fire} disabled={loading}>
        <Icon name="play" size={14} /> {loading ? "Firing…" : "Fire event"}
      </button>
      {result && (
        <div style={{ marginTop: 12, fontSize: 12 }} className="muted">
          <Pill variant={result.decision}>{result.decision}</Pill>{" "}
          {result.hitl_required ? "sent to HITL queue" : "auto-executed"}
        </div>
      )}
      {error && <div style={{ color: "var(--red)", fontSize: 12, marginTop: 10 }}>{error}</div>}
    </>
  );
}

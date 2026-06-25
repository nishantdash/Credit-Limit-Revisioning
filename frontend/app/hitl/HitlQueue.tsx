"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, Decision, inr, pct } from "../../lib/api";

export function HitlQueue({ initial }: { initial: Decision[] }) {
  const router = useRouter();
  const [items, setItems] = useState<Decision[]>(initial);
  const [busy, setBusy] = useState<string | null>(null);
  const [actor, setActor] = useState("credit.officer@bank");

  async function act(id: string, kind: "approve" | "reject") {
    setBusy(id);
    try {
      await api<Decision>(`/hitl/${id}/${kind}`, {
        method: "POST",
        body: JSON.stringify({ actor, notes: `Reviewed via dashboard` }),
      });
      setItems((cur) => cur.filter((d) => d.id !== id));
      router.refresh();
    } catch (e) {
      alert(`Failed: ${e}`);
    } finally {
      setBusy(null);
    }
  }

  if (items.length === 0) {
    return <div className="card muted">Queue empty.</div>;
  }

  return (
    <>
      <div className="row" style={{ marginBottom: 16, gap: 12 }}>
        <label className="muted" style={{ fontSize: 12 }}>Actor:</label>
        <input value={actor} onChange={(e) => setActor(e.target.value)} style={{ maxWidth: 320 }} />
      </div>
      <div className="grid" style={{ gap: 12 }}>
        {items.map((d) => (
          <div key={d.id} className="card">
            <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
              <div className="row" style={{ gap: 8 }}>
                <span className={`badge badge-${d.decision}`}>{d.decision}</span>
                <Link href={`/customers/${d.customer_id}`}>{d.customer_id}</Link>
                <span className="muted">· {d.id} · {d.trigger_type}</span>
              </div>
              <div className="row" style={{ gap: 8 }}>
                <button className="btn btn-success" onClick={() => act(d.id, "approve")} disabled={busy === d.id}>Approve & execute</button>
                <button className="btn btn-danger" onClick={() => act(d.id, "reject")} disabled={busy === d.id}>Reject</button>
              </div>
            </div>
            <div className="row" style={{ gap: 24, marginBottom: 8 }}>
              <div>
                <div className="metric-label">Limit</div>
                <div>{inr(d.current_limit)} → <strong>{inr(d.recommended_limit)}</strong></div>
                <div className="metric-sub">+{inr(d.recommended_limit - d.current_limit)}</div>
              </div>
              <div>
                <div className="metric-label">PD pre → post</div>
                <div>{pct(d.pd_pre)} → {pct(d.pd_post_projected)}</div>
              </div>
              <div>
                <div className="metric-label">Income est.</div>
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
                  <div className="metric-label">Tier change</div>
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
            <div style={{ marginTop: 10 }}>{d.explainer_text_officer}</div>
          </div>
        ))}
      </div>
    </>
  );
}

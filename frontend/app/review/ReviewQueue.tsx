"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, Decision, inr, DIRECTION_VARIANT, INTENT_VARIANT } from "../../lib/api";
import { Avatar } from "../../components/Avatar";
import { Icon } from "../../components/Icon";
import { Pill } from "../../components/Pill";

export function ReviewQueue({ initial }: { initial: Decision[] }) {
  const router = useRouter();
  const [items, setItems] = useState<Decision[]>(initial);
  const [busy, setBusy] = useState<string | null>(null);
  const [actor, setActor] = useState("credit.officer@apexbank");

  async function act(id: string, kind: "approve" | "reject") {
    setBusy(id);
    try {
      await api(`/review/${id}/${kind}`, {
        method: "POST",
        body: JSON.stringify({ actor, notes: "Reviewed via dashboard" }),
      });
      setItems((cur) => cur.filter((d) => d.id !== id));
      router.refresh();
    } catch (e) {
      alert(`Failed: ${e}`);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="card padless">
      <div className="card-head">
        <h3>Pending review</h3>
        <div className="row" style={{ gap: 8 }}>
          <span className="muted" style={{ fontSize: 12 }}>Acting as</span>
          <input value={actor} onChange={(e) => setActor(e.target.value)} style={{ width: 220, padding: "6px 10px", fontSize: 12 }} />
        </div>
      </div>
      {items.length === 0 ? (
        <div className="empty">Queue empty — every low-confidence decision has been actioned.</div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Customer</th><th>Cell</th><th>Intent</th><th>Proposed</th><th>Why review</th><th>Conf</th><th></th></tr>
            </thead>
            <tbody>
              {items.map((d) => (
                <tr key={d.id}>
                  <td>
                    <Link href={`/customers/${d.customer_id}`} className="row" style={{ gap: 10, color: "var(--text)" }}>
                      <Avatar id={d.customer_id} size="sm" /><span>{d.customer_id}</span>
                    </Link>
                  </td>
                  <td className="muted" style={{ fontSize: 12 }}>{d.matrix_cell}</td>
                  <td><Pill variant={INTENT_VARIANT[d.intent]} bare>{d.intent}</Pill></td>
                  <td>
                    <Pill variant={DIRECTION_VARIANT[d.direction]}>{d.direction}</Pill>{" "}
                    {d.direction !== "MAINTAIN" && <span className="muted" style={{ fontSize: 12 }}>{inr(d.current_limit)} → {inr(d.recommended_limit)}</span>}
                  </td>
                  <td><div className="reasons">{(d.applied_caps.length ? d.applied_caps : ["LOW_CONFIDENCE"]).map((c) => <span key={c} className="chip">{c}</span>)}</div></td>
                  <td className="muted">{(d.confidence * 100).toFixed(0)}%</td>
                  <td>
                    <div className="row" style={{ gap: 6 }}>
                      <button className="btn btn-success btn-sm" disabled={busy === d.id} onClick={() => act(d.id, "approve")}><Icon name="check" size={13} /> Approve</button>
                      <button className="btn btn-danger btn-sm" disabled={busy === d.id} onClick={() => act(d.id, "reject")}><Icon name="x" size={13} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

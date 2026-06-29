"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, Decision, inr, INTENT_VARIANT } from "../../lib/api";
import { Avatar } from "../../components/Avatar";
import { Icon } from "../../components/Icon";
import { Pill } from "../../components/Pill";

export function OffersClient({ initial }: { initial: Decision[] }) {
  const router = useRouter();
  const [items, setItems] = useState<Decision[]>(initial);
  const [busy, setBusy] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);

  async function act(id: string, kind: "consent" | "decline", channel?: string) {
    setBusy(id);
    try {
      await api(`/offers/${id}/${kind}`, {
        method: "POST",
        body: JSON.stringify({ actor: "customer", channel }),
      });
      setItems((cur) => cur.filter((d) => d.id !== id));
      setOpen(null);
      router.refresh();
    } catch (e) {
      alert(`Failed: ${e}`);
    } finally {
      setBusy(null);
    }
  }

  if (items.length === 0) {
    return <div className="card"><div className="empty">No offers awaiting consent. Run a micro-review sweep to generate increase offers.</div></div>;
  }

  return (
    <div className="grid" style={{ gap: 14 }}>
      {items.map((d) => {
        const delta = d.recommended_limit - d.current_limit;
        const expanded = open === d.id;
        return (
          <div key={d.id} className="card">
            <div className="row-between" style={{ marginBottom: 14 }}>
              <div className="row" style={{ gap: 12 }}>
                <Avatar id={d.customer_id} />
                <div style={{ lineHeight: 1.3 }}>
                  <Link href={`/customers/${d.customer_id}`} style={{ color: "var(--text)", fontWeight: 600 }}>{d.customer_id}</Link>
                  <div className="row" style={{ gap: 6, marginTop: 2 }}>
                    <Pill variant={INTENT_VARIANT[d.intent]} bare>{d.intent}</Pill>
                    <span className="muted" style={{ fontSize: 12 }}>{d.matrix_cell}</span>
                    {d.duration === "TEMPORARY" && <Pill variant="TEMPORARY" bare>temporary · auto-reverts</Pill>}
                  </div>
                </div>
              </div>
              <Pill variant="PENDING_CONSENT">Awaiting OTP/MPIN</Pill>
            </div>

            <div className="meta-row" style={{ marginBottom: 14 }}>
              <div className="meta-cell">
                <span className="lbl">Limit increase</span>
                <span className="val row" style={{ gap: 6 }}>
                  {inr(d.current_limit)} <Icon name="arrow-right" size={12} /> <strong>{inr(d.recommended_limit)}</strong>
                  <span style={{ color: "var(--green)", fontSize: 12 }}>+{d.magnitude_pct.toFixed(1)}%</span>
                </span>
              </div>
              <div className="meta-cell"><span className="lbl">Increase amount</span><span className="val">{inr(delta)}</span></div>
              <div className="meta-cell"><span className="lbl">Capacity headroom</span><span className="val">{inr(d.capacity_headroom)}</span></div>
              <div className="meta-cell"><span className="lbl">Confidence</span><span className="val">{(d.confidence * 100).toFixed(0)}%</span></div>
              <div className="meta-cell"><span className="lbl">Channel</span><span className="val">{d.consent_channel ?? "OTP"}</span></div>
            </div>

            <div style={{ background: "var(--surface-2)", borderRadius: 8, padding: 12, fontSize: 13, marginBottom: 14 }}>
              <div className="muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 4 }}>Consent copy — value-framed (§6.3)</div>
              {d.consent_copy || d.explainer_customer}
            </div>

            {d.applied_caps.length > 0 && (
              <div className="reasons" style={{ marginBottom: 14 }}>
                {d.applied_caps.map((c) => <span key={c} className="chip">{c}</span>)}
              </div>
            )}

            <div className="row" style={{ gap: 8 }}>
              <button className="btn btn-success" disabled={busy === d.id} onClick={() => act(d.id, "consent", "OTP")}>
                <Icon name="check" size={14} /> Approve via OTP
              </button>
              <button className="btn" disabled={busy === d.id} onClick={() => act(d.id, "consent", "MPIN")}>
                Approve via MPIN
              </button>
              <button className="btn btn-danger" disabled={busy === d.id} onClick={() => act(d.id, "decline")}>
                <Icon name="x" size={14} /> Decline
              </button>
              <button className="btn btn-sm" style={{ marginLeft: "auto" }} onClick={() => setOpen(expanded ? null : d.id)}>
                {expanded ? "Hide" : "Officer note"}
              </button>
            </div>

            {expanded && (
              <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--border)", fontSize: 13 }}>
                {d.explainer_officer}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

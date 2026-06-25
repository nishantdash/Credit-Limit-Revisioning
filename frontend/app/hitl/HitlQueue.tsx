"use client";
import { Fragment, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, Decision, inr, pct } from "../../lib/api";
import { Avatar } from "../../components/Avatar";
import { Icon } from "../../components/Icon";
import { Pill } from "../../components/Pill";

type Tab = "pending" | "decided" | "all";

export function HitlQueue({
  initial,
  pendingCount,
  decidedCount,
  totalCount,
}: {
  initial: Decision[];
  pendingCount: number;
  decidedCount: number;
  totalCount: number;
}) {
  const router = useRouter();
  const [items, setItems] = useState<Decision[]>(initial);
  const [busy, setBusy] = useState<string | null>(null);
  const [actor, setActor] = useState("credit.officer@yesbank");
  const [tab, setTab] = useState<Tab>("pending");
  const [openId, setOpenId] = useState<string | null>(null);

  async function act(id: string, kind: "approve" | "reject") {
    setBusy(id);
    try {
      await api<Decision>(`/hitl/${id}/${kind}`, {
        method: "POST",
        body: JSON.stringify({ actor, notes: "Reviewed via dashboard" }),
      });
      setItems((cur) => cur.filter((d) => d.id !== id));
      setOpenId(null);
      router.refresh();
    } catch (e) {
      alert(`Failed: ${e}`);
    } finally {
      setBusy(null);
    }
  }

  const rows = items;

  return (
    <div className="card padless">
      <div style={{ padding: "12px 20px 0" }}>
        <div className="tabs" style={{ marginBottom: 0 }}>
          <button className={`tab ${tab === "pending" ? "active" : ""}`} onClick={() => setTab("pending")}>
            Pending <span className="count">{pendingCount}</span>
          </button>
          <button className={`tab ${tab === "decided" ? "active" : ""}`} onClick={() => setTab("decided")}>
            Decided <span className="count">{decidedCount}</span>
          </button>
          <button className={`tab ${tab === "all" ? "active" : ""}`} onClick={() => setTab("all")}>
            All <span className="count">{totalCount}</span>
          </button>
          <div className="row" style={{ marginLeft: "auto", padding: "4px 0", gap: 8 }}>
            <span className="muted" style={{ fontSize: 12 }}>Acting as</span>
            <input value={actor} onChange={(e) => setActor(e.target.value)} style={{ width: 220, padding: "6px 10px", fontSize: 12 }} />
          </div>
        </div>
      </div>

      {rows.length === 0 ? (
        <div className="empty">
          {tab === "pending" ? "Queue empty — every flagged decision has been actioned." : "Nothing to show."}
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Cardholder</th>
                <th>Request</th>
                <th>Current → Recommended</th>
                <th>PD</th>
                <th>Raised</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((d) => {
                const expanded = openId === d.id;
                const delta = d.recommended_limit - d.current_limit;
                const pctDelta = d.current_limit ? (delta / d.current_limit) * 100 : 0;
                return (
                  <Fragment key={d.id}>
                    <tr>
                      <td>
                        <div className="row" style={{ gap: 10 }}>
                          <Avatar id={d.customer_id} />
                          <div style={{ lineHeight: 1.2 }}>
                            <div style={{ fontWeight: 600, color: "var(--text)" }}>
                              <Link href={`/customers/${d.customer_id}`} style={{ color: "var(--text)" }}>{d.customer_id}</Link>
                            </div>
                            <div style={{ fontSize: 11, color: "var(--text-dim)" }} className="mono">{d.id}</div>
                          </div>
                        </div>
                      </td>
                      <td>
                        <div className="row" style={{ gap: 6 }}>
                          <Pill variant={d.decision}>{d.decision}</Pill>
                          <span className="chip">{d.trigger_type}</span>
                        </div>
                      </td>
                      <td>
                        <div className="row" style={{ gap: 6 }}>
                          <span>{inr(d.current_limit)}</span>
                          <Icon name="arrow-right" size={12} />
                          <strong>{inr(d.recommended_limit)}</strong>
                          <span style={{ color: pctDelta >= 0 ? "var(--green)" : "var(--red)", fontSize: 12 }}>
                            {pctDelta >= 0 ? "+" : ""}{pctDelta.toFixed(0)}%
                          </span>
                        </div>
                      </td>
                      <td className="muted">{pct(d.pd_pre)} → {pct(d.pd_post_projected)}</td>
                      <td className="muted">{new Date(d.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}</td>
                      <td><Pill variant="PENDING">Pending</Pill></td>
                      <td>
                        <button className="btn btn-primary btn-sm" onClick={() => setOpenId(expanded ? null : d.id)}>
                          {expanded ? "Close" : "Review"}
                        </button>
                      </td>
                    </tr>
                    {expanded && (
                      <tr>
                        <td colSpan={7} style={{ background: "var(--surface-2)", padding: 0 }}>
                          <div style={{ padding: 20 }}>
                            <div className="meta-row" style={{ marginBottom: 14 }}>
                              <div className="meta-cell"><span className="lbl">Income est.</span><span className="val">{inr(d.income_estimate)}/mo</span></div>
                              <div className="meta-cell"><span className="lbl">Behavioral</span><span className="val">{d.behavioral_score.toFixed(0)}/100</span></div>
                              <div className="meta-cell"><span className="lbl">Confidence</span><span className="val">{(d.confidence * 100).toFixed(0)}%</span></div>
                              {d.benefits_tier_to && d.benefits_tier_to !== d.benefits_tier_from && (
                                <div className="meta-cell">
                                  <span className="lbl">Benefits tier change</span>
                                  <span className="val row" style={{ gap: 4 }}>
                                    <Pill variant={d.benefits_tier_from as "SILVER" | "GOLD" | "PLATINUM"} bare>{d.benefits_tier_from}</Pill>
                                    <Icon name="arrow-right" size={12} />
                                    <Pill variant={d.benefits_tier_to as "SILVER" | "GOLD" | "PLATINUM"} bare>{d.benefits_tier_to}</Pill>
                                  </span>
                                </div>
                              )}
                            </div>
                            <div className="reasons" style={{ marginBottom: 14 }}>
                              {d.reason_codes.map((r) => <span key={r} className="chip">{r}</span>)}
                            </div>
                            <div style={{ background: "var(--surface)", padding: 14, borderRadius: 8, border: "1px solid var(--border)", marginBottom: 14, fontSize: 13 }}>
                              <div className="muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 4 }}>Officer note</div>
                              {d.explainer_text_officer}
                            </div>
                            <div className="row" style={{ gap: 8 }}>
                              <button className="btn btn-success" onClick={() => act(d.id, "approve")} disabled={busy === d.id}>
                                <Icon name="check" size={14} /> Approve & execute
                              </button>
                              <button className="btn btn-danger" onClick={() => act(d.id, "reject")} disabled={busy === d.id}>
                                <Icon name="x" size={14} /> Reject
                              </button>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

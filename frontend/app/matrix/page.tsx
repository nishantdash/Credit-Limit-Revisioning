import Link from "next/link";
import { api, Decision, TIER_LABEL } from "../../lib/api";
import { Icon } from "../../components/Icon";
import { Pill } from "../../components/Pill";

type Cell = { dir: string; note: string; kind: "inc" | "dec" | "frz" | "" };

// Mirrors backend matrix._MATRIX (§4.2). Columns are the three intents; seasonal
// is handled as a temporary variant inside the growth/neutral cells.
const COLS = ["GROWTH", "NEUTRAL", "DISTRESS"];
const COL_LABEL: Record<string, string> = { GROWTH: "Growth intent", NEUTRAL: "Neutral / maintenance", DISTRESS: "Distress intent" };

const MATRIX: Record<number, Record<string, Cell>> = {
  1: {
    GROWTH: { dir: "Aggressive ↑", note: "Instant, permanent increase", kind: "inc" },
    NEUTRAL: { dir: "Maintain", note: "Capital-lock at low utilisation", kind: "" },
    DISTRESS: { dir: "Hold + observe", note: "Likely seasonal → temporary ↑", kind: "" },
  },
  2: {
    GROWTH: { dir: "Moderate ↑", note: "Step-up increase", kind: "inc" },
    NEUTRAL: { dir: "Maintain", note: "Stable revolver", kind: "" },
    DISTRESS: { dir: "Hold + soft engage", note: "Freeze velocity", kind: "" },
  },
  3: {
    GROWTH: { dir: "Cautious temp ↑", note: "Do not auto-cut a growing customer", kind: "inc" },
    NEUTRAL: { dir: "↓ slowly", note: "Gentle decrease", kind: "dec" },
    DISTRESS: { dir: "↓ sharply", note: "Decrease + restructure offer", kind: "dec" },
  },
  4: {
    GROWTH: { dir: "Freeze", note: "Regardless of intent", kind: "frz" },
    NEUTRAL: { dir: "Freeze", note: "Binary block", kind: "frz" },
    DISTRESS: { dir: "Collapse", note: "To obligation", kind: "dec" },
  },
};

function bucketIntent(intent: string): string {
  if (intent === "GROWTH") return "GROWTH";
  if (intent === "DISTRESS" || intent === "KNOCKOUT") return "DISTRESS";
  if (intent === "SEASONAL") return "GROWTH";
  return "NEUTRAL";
}

export default async function MatrixPage() {
  const decisions = await api<Decision[]>("/decisions?limit=500");

  // Latest decision per customer, counted into cells.
  const latest = new Map<string, Decision>();
  for (const d of decisions) if (!latest.has(d.customer_id)) latest.set(d.customer_id, d);
  const counts: Record<string, Decision[]> = {};
  for (const d of latest.values()) {
    const key = `${d.risk_tier}:${bucketIntent(d.intent)}`;
    (counts[key] ??= []).push(d);
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h2 className="page-title">Risk × Intent matrix</h2>
          <p className="page-sub" style={{ marginBottom: 0 }}>
            The reframed decision surface — utilisation is demoted to a magnitude modifier (§4.2).
          </p>
        </div>
      </div>

      <div className="banner" style={{ marginBottom: 24 }}>
        <Icon name="info" size={18} />
        <div>
          <span className="banner-title">The cell the conventional model gets wrong: Tier 3 × Growth.</span>{" "}
          An orthodox engine cuts any subprime account. A subprime customer with rising category quality and
          stabilising inflow is a future Tier 2 — so the engine holds or cautiously, temporarily extends instead.
        </div>
      </div>

      <div className="card">
        <div className="matrix-grid">
          <div className="mh"></div>
          {COLS.map((c) => <div key={c} className="mh" style={{ justifyContent: "center" }}>{COL_LABEL[c]}</div>)}

          {[1, 2, 3, 4].map((tier) => (
            <Row key={tier} tier={tier} counts={counts} />
          ))}
        </div>
      </div>
    </>
  );
}

function Row({ tier, counts }: { tier: number; counts: Record<string, Decision[]> }) {
  const tierColor = tier === 1 ? "var(--green-tint)" : tier === 2 ? "var(--primary-tint)" : tier === 3 ? "var(--amber-tint)" : "var(--red-tint)";
  return (
    <>
      <div className="rh" style={{ background: tierColor }}>
        <span>{TIER_LABEL[tier].split(" · ")[0]}</span>
        <span style={{ fontWeight: 400, fontSize: 11, color: "var(--text-dim)" }}>{TIER_LABEL[tier].split(" · ")[1]}</span>
      </div>
      {COLS.map((col) => {
        const cell = MATRIX[tier][col];
        const here = counts[`${tier}:${col}`] || [];
        const hot = tier === 3 && col === "GROWTH";
        return (
          <div key={col} className={`matrix-cell ${cell.kind} ${hot ? "hot" : ""}`}>
            <div className="mc-dir">{cell.dir}</div>
            <div className="mc-note">{cell.note}</div>
            <div className="mc-count">
              {here.length === 0 ? <span>—</span> : (
                <div className="row" style={{ gap: 4, flexWrap: "wrap" }}>
                  {here.map((d) => (
                    <Link key={d.id} href={`/customers/${d.customer_id}`} style={{ textDecoration: "none" }}>
                      <Pill variant="gray" bare>{d.customer_id.replace("CIF-", "")}</Pill>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </>
  );
}

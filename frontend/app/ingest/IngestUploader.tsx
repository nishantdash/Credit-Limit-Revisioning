"use client";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  api,
  CohortSweepResponse,
  Decision,
  IngestSummary,
  inr,
  uploadFile,
} from "../../lib/api";

type Preview = { headers: string[]; rows: string[][]; rowCount: number };

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

export function IngestUploader() {
  const router = useRouter();
  const fileInput = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [dragging, setDragging] = useState(false);

  const [summary, setSummary] = useState<IngestSummary | null>(null);
  const [sweep, setSweep] = useState<CohortSweepResponse | null>(null);
  const [busy, setBusy] = useState<"idle" | "ingesting" | "sweeping">("idle");
  const [error, setError] = useState<string | null>(null);

  async function selectFile(f: File | null) {
    setFile(f);
    setSummary(null);
    setSweep(null);
    setError(null);
    if (!f) { setPreview(null); return; }
    const text = await f.text();
    const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
    if (lines.length === 0) { setPreview(null); return; }
    const headers = parseCsvLine(lines[0]);
    const body = lines.slice(1, 11).map(parseCsvLine);
    setPreview({ headers, rows: body, rowCount: lines.length - 1 });
  }

  async function ingest() {
    if (!file) return;
    setBusy("ingesting"); setError(null); setSummary(null); setSweep(null);
    try {
      const result = await uploadFile<IngestSummary>("/ingest/transactions-csv", file);
      setSummary(result);
      router.refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy("idle");
    }
  }

  async function runSweep() {
    if (!summary || summary.known_customer_ids.length === 0) return;
    setBusy("sweeping"); setError(null); setSweep(null);
    try {
      const result = await api<CohortSweepResponse>("/ingest/cohort-sweep", {
        method: "POST",
        body: JSON.stringify({ customer_ids: summary.known_customer_ids }),
      });
      setSweep(result);
      router.refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy("idle");
    }
  }

  function reset() {
    setFile(null); setPreview(null); setSummary(null); setSweep(null); setError(null);
    if (fileInput.current) fileInput.current.value = "";
  }

  return (
    <>
      <div className="card">
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            const f = e.dataTransfer.files?.[0] ?? null;
            if (f) selectFile(f);
          }}
          style={{
            border: `2px dashed ${dragging ? "var(--accent)" : "var(--border)"}`,
            borderRadius: 10,
            padding: 32,
            textAlign: "center",
            background: dragging ? "rgba(91,141,239,0.05)" : "transparent",
            transition: "all 120ms ease",
          }}
        >
          <div style={{ fontSize: 16, marginBottom: 8 }}>
            {file ? <strong>{file.name}</strong> : "Drop a CSV here, or click to pick a file"}
          </div>
          <div className="muted" style={{ fontSize: 12 }}>
            Required column: <code>customer_id</code>. Optional:{" "}
            <code>timestamp, amount, merchant_category, merchant_tier, merchant_city</code>.
          </div>
          <input
            ref={fileInput}
            type="file"
            accept=".csv,text/csv"
            style={{ display: "none" }}
            onChange={(e) => selectFile(e.target.files?.[0] ?? null)}
          />
          <div className="row" style={{ justifyContent: "center", marginTop: 16, gap: 12 }}>
            <button className="btn" onClick={() => fileInput.current?.click()}>
              {file ? "Pick a different file" : "Pick CSV"}
            </button>
            <a className="btn" href={`${API_BASE}/ingest/sample-csv`} download>
              Download sample CSV
            </a>
            {file && <button className="btn" onClick={reset}>Reset</button>}
          </div>
        </div>
      </div>

      {preview && (
        <>
          <div style={{ height: 16 }} />
          <div className="card">
            <div className="row" style={{ justifyContent: "space-between", marginBottom: 12 }}>
              <h3 style={{ margin: 0 }}>Preview</h3>
              <span className="muted">{preview.rowCount} rows · showing first {preview.rows.length}</span>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table>
                <thead>
                  <tr>{preview.headers.map((h, i) => <th key={i}>{h}</th>)}</tr>
                </thead>
                <tbody>
                  {preview.rows.map((r, i) => (
                    <tr key={i}>
                      {r.map((c, j) => <td key={j}>{c}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="row" style={{ marginTop: 16, gap: 12 }}>
              <button className="btn btn-primary" onClick={ingest} disabled={busy !== "idle"}>
                {busy === "ingesting" ? "Ingesting…" : "Ingest transactions"}
              </button>
              <span className="muted" style={{ fontSize: 12 }}>
                Rows attach to existing customers. Unknown CIFs are surfaced but skipped.
              </span>
            </div>
          </div>
        </>
      )}

      {error && (
        <>
          <div style={{ height: 16 }} />
          <div className="card" style={{ borderColor: "var(--red)" }}>
            <strong style={{ color: "var(--red)" }}>Error</strong>
            <pre className="code" style={{ marginTop: 8 }}>{error}</pre>
          </div>
        </>
      )}

      {summary && <IngestSummaryCard summary={summary} onRun={runSweep} busy={busy === "sweeping"} />}
      {sweep && <SweepResults sweep={sweep} />}
    </>
  );
}

function IngestSummaryCard({ summary, onRun, busy }: { summary: IngestSummary; onRun: () => void; busy: boolean }) {
  const cohortSize = summary.known_customer_ids.length;
  return (
    <>
      <div style={{ height: 16 }} />
      <div className="card">
        <h3 style={{ marginTop: 0 }}>Ingestion summary</h3>
        <div className="grid cols-4">
          <Stat label="Rows parsed" value={summary.rows_total.toString()} />
          <Stat label="Txns ingested" value={summary.transactions_ingested.toString()} />
          <Stat label="Known customers" value={summary.known_customer_ids.length.toString()} accent="green" />
          <Stat label="Unknown customers" value={summary.unknown_customer_ids.length.toString()} accent={summary.unknown_customer_ids.length ? "amber" : undefined} />
        </div>

        {summary.unknown_customer_ids.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <div className="metric-label">Skipped (not in CLR roster)</div>
            <div className="reasons" style={{ marginTop: 6 }}>
              {summary.unknown_customer_ids.map((c) => <span key={c} className="reason-chip">{c}</span>)}
            </div>
          </div>
        )}

        {summary.errors.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <div className="metric-label">Errors</div>
            <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>
              {summary.errors.map((e, i) => <li key={i} className="muted">{e}</li>)}
            </ul>
          </div>
        )}

        <div className="divider" />

        <div className="row" style={{ justifyContent: "space-between" }}>
          <div>
            <div className="metric-label">Cohort ready</div>
            <div className="metric-value" style={{ fontSize: 18 }}>{cohortSize} customers</div>
            <div className="metric-sub">{summary.known_customer_ids.join(", ") || "—"}</div>
          </div>
          <button className="btn btn-primary" onClick={onRun} disabled={busy || cohortSize === 0}>
            {busy ? "Running CLR on cohort…" : `Run CLR on ${cohortSize} customers →`}
          </button>
        </div>
      </div>
    </>
  );
}

function SweepResults({ sweep }: { sweep: CohortSweepResponse }) {
  const byDecision = { UPGRADE: 0, DOWNGRADE: 0, FREEZE: 0 } as Record<string, number>;
  const hitlCount = sweep.decisions.filter((d) => d.hitl_required).length;
  const executedCount = sweep.decisions.filter((d) => d.executed).length;
  const uplift = sweep.decisions
    .filter((d) => d.decision === "UPGRADE")
    .reduce((s, d) => s + (d.recommended_limit - d.current_limit), 0);
  sweep.decisions.forEach((d) => { byDecision[d.decision] = (byDecision[d.decision] || 0) + 1; });
  return (
    <>
      <div style={{ height: 16 }} />
      <div className="card">
        <h3 style={{ marginTop: 0 }}>Cohort sweep results</h3>
        <div className="grid cols-4">
          <Stat label="Upgrades" value={(byDecision.UPGRADE || 0).toString()} accent="green" />
          <Stat label="Downgrades" value={(byDecision.DOWNGRADE || 0).toString()} accent="red" />
          <Stat label="Freezes" value={(byDecision.FREEZE || 0).toString()} accent="amber" />
          <Stat label="Recommended uplift" value={inr(uplift)} sub={`${hitlCount} routed to HITL · ${executedCount} auto-executed`} />
        </div>
        <div style={{ height: 16 }} />
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th>Decision</th>
                <th>Customer</th>
                <th>Limit change</th>
                <th>PD pre → post</th>
                <th>Reason codes</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {sweep.decisions.map((d: Decision) => (
                <tr key={d.id}>
                  <td><span className={`badge badge-${d.decision}`}>{d.decision}</span></td>
                  <td><Link href={`/customers/${d.customer_id}`}>{d.customer_id}</Link></td>
                  <td>
                    {d.decision === "FREEZE"
                      ? <span className="muted">{inr(d.current_limit)}</span>
                      : <>{inr(d.current_limit)} → <strong>{inr(d.recommended_limit)}</strong></>}
                  </td>
                  <td className="muted">{(d.pd_pre * 100).toFixed(2)}% → {(d.pd_post_projected * 100).toFixed(2)}%</td>
                  <td>
                    <div className="reasons">
                      {d.reason_codes.slice(0, 3).map((r) => <span key={r} className="reason-chip">{r}</span>)}
                    </div>
                  </td>
                  <td>
                    {d.hitl_required
                      ? <span className={`badge badge-${d.hitl_status}`}>HITL · {d.hitl_status}</span>
                      : d.executed
                        ? <span className="badge badge-APPROVED">EXECUTED</span>
                        : <span className="muted">—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {sweep.skipped_unknown.length > 0 && (
          <div className="metric-sub" style={{ marginTop: 12 }}>
            Skipped: {sweep.skipped_unknown.join(", ")}
          </div>
        )}
      </div>
    </>
  );
}

function Stat({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent?: "green" | "red" | "amber" }) {
  const color = accent === "green" ? "var(--green)" : accent === "red" ? "var(--red)" : accent === "amber" ? "var(--amber)" : undefined;
  return (
    <div className="card">
      <div className="metric-label">{label}</div>
      <div className="metric-value" style={{ color, fontSize: 22 }}>{value}</div>
      {sub && <div className="metric-sub">{sub}</div>}
    </div>
  );
}

// Minimal CSV line parser — handles double-quoted fields with commas/quotes inside.
function parseCsvLine(line: string): string[] {
  const out: string[] = [];
  let cur = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (inQuotes) {
      if (c === '"') {
        if (line[i + 1] === '"') { cur += '"'; i++; }
        else inQuotes = false;
      } else cur += c;
    } else {
      if (c === ",") { out.push(cur); cur = ""; }
      else if (c === '"') inQuotes = true;
      else cur += c;
    }
  }
  out.push(cur);
  return out;
}

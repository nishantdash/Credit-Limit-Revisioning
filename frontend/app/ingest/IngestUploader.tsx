"use client";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  api,
  CohortSweepResponse,
  Decision,
  DIRECTION_VARIANT,
  IngestSummary,
  INTENT_VARIANT,
  inr,
  uploadFile,
} from "../../lib/api";
import { Avatar } from "../../components/Avatar";
import { Icon } from "../../components/Icon";
import { Pill } from "../../components/Pill";

type Preview = { headers: string[]; rows: string[][]; rowCount: number };

const SWEEP_BATCH = 250; // matches backend MAX_COHORT_SWEEP

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
    setFile(f); setSummary(null); setSweep(null); setError(null);
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
    } catch (e: unknown) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy("idle"); }
  }

  async function runSweep() {
    if (!summary || summary.known_customer_ids.length === 0) return;
    setBusy("sweeping"); setError(null);
    // Sweep only customers not yet scored so re-running advances the cohort
    // (the backend caps each request at 250 to stay responsive).
    const swept = new Set(sweep?.decisions.map((d) => d.customer_id) ?? []);
    const remaining = summary.known_customer_ids.filter((id) => !swept.has(id));
    const batch = remaining.length ? remaining : summary.known_customer_ids;
    try {
      const result = await api<CohortSweepResponse>("/ingest/cohort-sweep", {
        method: "POST",
        body: JSON.stringify({ customer_ids: batch }),
      });
      const prior = sweep?.decisions.filter((d) => !result.decisions.some((r) => r.id === d.id)) ?? [];
      setSweep({ ...result, decisions: [...prior, ...result.decisions] });
      router.refresh();
    } catch (e: unknown) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy("idle"); }
  }

  function reset() {
    setFile(null); setPreview(null); setSummary(null); setSweep(null); setError(null);
    if (fileInput.current) fileInput.current.value = "";
  }

  const sweptCount = sweep?.decisions.length ?? 0;
  const cohortSize = summary?.known_customer_ids.length ?? 0;
  const remainingCount = Math.max(0, cohortSize - sweptCount);

  return (
    <div className="grid" style={{ gap: 16 }}>
      <div className="card">
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault(); setDragging(false);
            const f = e.dataTransfer.files?.[0] ?? null;
            if (f) selectFile(f);
          }}
          style={{
            border: `2px dashed ${dragging ? "var(--primary)" : "var(--border-strong)"}`,
            borderRadius: 10,
            padding: 36,
            textAlign: "center",
            background: dragging ? "var(--primary-tint)" : "var(--surface-2)",
            transition: "all 150ms ease",
          }}
        >
          <div style={{ width: 48, height: 48, borderRadius: 12, background: "var(--primary-tint)", color: "var(--primary)", display: "grid", placeItems: "center", margin: "0 auto 12px" }}>
            <Icon name="upload" size={22} />
          </div>
          <div style={{ fontSize: 15, marginBottom: 4, fontWeight: 600 }}>
            {file ? file.name : "Drop a CSV here, or click to pick a file"}
          </div>
          <div className="muted" style={{ fontSize: 12 }}>
            {file ? `${(file.size / 1024).toFixed(1)} KB` : "Must contain a customer_id column"}
          </div>
          <input
            ref={fileInput} type="file" accept=".csv,text/csv" style={{ display: "none" }}
            onChange={(e) => selectFile(e.target.files?.[0] ?? null)}
          />
          <div className="row" style={{ justifyContent: "center", marginTop: 16, gap: 8 }}>
            <button className="btn btn-primary" onClick={() => fileInput.current?.click()}>
              {file ? "Pick different file" : "Browse files"}
            </button>
            {file && <button className="btn" onClick={reset}>Reset</button>}
          </div>
        </div>
      </div>

      {preview && (
        <div className="card padless">
          <div className="card-head">
            <h3>Preview</h3>
            <span className="muted" style={{ fontSize: 12 }}>{preview.rowCount} rows · showing first {preview.rows.length}</span>
          </div>
          <div className="table-wrap">
            <table>
              <thead><tr>{preview.headers.map((h, i) => <th key={i}>{h}</th>)}</tr></thead>
              <tbody>{preview.rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j}>{c}</td>)}</tr>)}</tbody>
            </table>
          </div>
          <div style={{ padding: 16, borderTop: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span className="muted" style={{ fontSize: 12 }}>Rows attach to existing customers. Unknown CIFs are flagged but skipped.</span>
            <button className="btn btn-primary" onClick={ingest} disabled={busy !== "idle"}>
              {busy === "ingesting" ? "Ingesting…" : <>Ingest transactions <Icon name="arrow-right" size={14} /></>}
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="banner red"><Icon name="alert-circle" size={18} /><div><span className="banner-title">Error</span><div>{error}</div></div></div>
      )}

      {summary && (
        <div className="card">
          <h3 style={{ marginBottom: 16 }}>Ingestion summary</h3>
          <div className="grid cols-4" style={{ marginBottom: 16 }}>
            <Stat label="Rows parsed" value={summary.rows_total.toString()} />
            <Stat label="Txns ingested" value={summary.transactions_ingested.toString()} />
            <Stat label="Attached to roster" value={(summary.known_customer_ids.length - summary.created_customer_ids.length).toString()} color="green" />
            <Stat label="New customers" value={summary.created_customer_ids.length.toString()} color={summary.created_customer_ids.length ? "green" : undefined} />
          </div>

          {summary.created_customer_ids.length > 0 && (
            <div className="banner" style={{ marginBottom: 14 }}>
              <Icon name="users" size={18} />
              <div>
                <span className="banner-title">{summary.created_customer_ids.length} new customer{summary.created_customer_ids.length > 1 ? "s" : ""} created from the file.</span>
                <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>IDs not in the roster were bootstrapped — profile derived from uploaded spend (override with name / income / limit / bureau_score columns).</div>
                <div className="reasons" style={{ marginTop: 8 }}>
                  {summary.created_customer_ids.map((c) => <span key={c} className="chip">{c}</span>)}
                </div>
              </div>
            </div>
          )}

          {summary.unknown_customer_ids.length > 0 && (
            <div className="banner amber" style={{ marginBottom: 14 }}>
              <Icon name="alert-circle" size={18} />
              <div>
                <span className="banner-title">{summary.unknown_customer_ids.length} row group{summary.unknown_customer_ids.length > 1 ? "s" : ""} skipped.</span>
                <div className="reasons" style={{ marginTop: 8 }}>
                  {summary.unknown_customer_ids.map((c) => <span key={c} className="chip">{c}</span>)}
                </div>
              </div>
            </div>
          )}

          {summary.errors.length > 0 && (
            <div style={{ marginBottom: 14 }}>
              <div className="muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 6 }}>Errors</div>
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, color: "var(--text-2)" }}>
                {summary.errors.map((e, i) => <li key={i}>{e}</li>)}
              </ul>
            </div>
          )}

          <div className="card-divider" />

          <div className="row-between">
            <div>
              <div style={{ fontWeight: 600 }}>
                Cohort ready · {summary.known_customer_ids.length} customers
                {sweptCount > 0 && <span className="muted" style={{ fontWeight: 400 }}> · {sweptCount} scored</span>}
              </div>
              <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                {summary.known_customer_ids.slice(0, 24).join(", ") || "—"}
                {summary.known_customer_ids.length > 24 && ` +${summary.known_customer_ids.length - 24} more`}
              </div>
            </div>
            <button className="btn btn-primary" onClick={runSweep} disabled={busy !== "idle" || remainingCount === 0}>
              <Icon name="bolt" size={14} />
              {busy === "sweeping"
                ? "Running CLR…"
                : sweptCount === 0
                ? `Run CLR on ${Math.min(SWEEP_BATCH, summary.known_customer_ids.length)} customers`
                : remainingCount > 0
                ? `Sweep next ${Math.min(SWEEP_BATCH, remainingCount)} · ${remainingCount} left`
                : "All scored ✓"}
            </button>
          </div>
        </div>
      )}

      {sweep && <SweepResults sweep={sweep} total={cohortSize} remaining={remainingCount} />}
    </div>
  );
}

function SweepResults({ sweep, total, remaining }: { sweep: CohortSweepResponse; total: number; remaining: number }) {
  const increases = sweep.decisions.filter((d) => d.direction === "INCREASE").length;
  const decreases = sweep.decisions.filter((d) => d.direction === "DECREASE").length;
  const holds = sweep.decisions.filter((d) => d.direction === "MAINTAIN" || d.direction === "FREEZE").length;
  const offers = sweep.decisions.filter((d) => d.pipeline === "OFFER").length;
  return (
    <div className="card padless">
      <div className="card-head">
        <h3>Cohort sweep results</h3>
        <span className="muted" style={{ fontSize: 12 }}>{offers} offers · {decreases} decreases applied</span>
      </div>
      <div style={{ padding: 16 }}>
        {remaining > 0 && (
          <div className="banner amber" style={{ marginBottom: 16 }}>
            <Icon name="info" size={18} />
            <div>
              <span className="banner-title">Scored {sweep.decisions.length} of {total} — {remaining} still to go.</span>
              <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>
                Each run scores up to {SWEEP_BATCH} customers to stay responsive. Click <strong>Sweep next</strong> above to continue through the cohort.
              </div>
            </div>
          </div>
        )}
        <div className="grid cols-4" style={{ marginBottom: 16 }}>
          <Stat label="Increase offers" value={increases.toString()} color="green" />
          <Stat label="Decreases" value={decreases.toString()} color="red" />
          <Stat label="Hold / freeze" value={holds.toString()} color="amber" />
          <Stat label="Scored" value={`${sweep.decisions.length}${total > sweep.decisions.length ? ` / ${total}` : ""}`} />
        </div>
      </div>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Intent</th><th>Customer</th><th>Cell</th><th>Decision</th><th>Pipeline</th></tr></thead>
          <tbody>
            {sweep.decisions.map((d: Decision) => (
              <tr key={d.id}>
                <td><Pill variant={INTENT_VARIANT[d.intent]} bare>{d.intent}</Pill></td>
                <td>
                  <div className="row" style={{ gap: 10 }}>
                    <Avatar id={d.customer_id} size="sm" />
                    <Link href={`/customers/${d.customer_id}`} style={{ color: "var(--text)" }}>{d.customer_id}</Link>
                  </div>
                </td>
                <td className="muted" style={{ fontSize: 12 }}>{d.matrix_cell}</td>
                <td>
                  <Pill variant={DIRECTION_VARIANT[d.direction]}>{d.direction}</Pill>{" "}
                  {d.direction !== "MAINTAIN" && d.direction !== "FREEZE" && <span className="muted" style={{ fontSize: 12 }}>{inr(d.current_limit)} <Icon name="arrow-right" size={11} /> {inr(d.recommended_limit)}</span>}
                </td>
                <td>{d.pipeline === "NONE" ? <span className="muted">—</span> : <Pill variant={d.pipeline} bare>{d.pipeline}</Pill>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {sweep.skipped_unknown.length > 0 && (
        <div style={{ padding: 12, fontSize: 12 }} className="muted">Skipped: {sweep.skipped_unknown.join(", ")}</div>
      )}
    </div>
  );
}

function Stat({ label, value, color }: { label: string; value: string; color?: "green" | "amber" | "red" }) {
  const c = color === "green" ? "var(--green)" : color === "red" ? "var(--red)" : color === "amber" ? "var(--amber)" : "var(--text)";
  return (
    <div style={{ background: "var(--surface-2)", borderRadius: 10, padding: 14 }}>
      <div className="muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.4, marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: c }}>{value}</div>
    </div>
  );
}

function parseCsvLine(line: string): string[] {
  const out: string[] = [];
  let cur = ""; let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (inQuotes) {
      if (c === '"') { if (line[i + 1] === '"') { cur += '"'; i++; } else inQuotes = false; }
      else cur += c;
    } else {
      if (c === ",") { out.push(cur); cur = ""; }
      else if (c === '"') inQuotes = true;
      else cur += c;
    }
  }
  out.push(cur);
  return out;
}

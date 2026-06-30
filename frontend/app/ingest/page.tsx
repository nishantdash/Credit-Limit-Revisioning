import { IngestUploader } from "./IngestUploader";
import { Icon } from "../../components/Icon";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

export default function IngestPage() {
  return (
    <>
      <div className="page-head">
        <div>
          <h2 className="page-title">Upload transaction dump</h2>
          <p className="page-sub" style={{ marginBottom: 0 }}>
            Upload a CSV export from CBS for a specific customer cohort, then run CLR on just that cohort.
          </p>
        </div>
      </div>

      <div className="grid split-2-1">
        <IngestUploader />

        <div className="grid" style={{ gap: 16, alignContent: "start" }}>
          <div className="card">
            <h3 style={{ marginBottom: 12 }}>Format</h3>
            <div style={{ fontSize: 13, color: "var(--text-2)" }}>
              <div style={{ marginBottom: 10 }}>
                <strong>Required column</strong>
                <div className="reasons" style={{ marginTop: 4 }}><span className="chip">customer_id</span></div>
              </div>
              <div style={{ marginBottom: 14 }}>
                <strong>Optional columns</strong>
                <div className="reasons" style={{ marginTop: 4 }}>
                  <span className="chip">timestamp</span>
                  <span className="chip">amount</span>
                  <span className="chip">category_class</span>
                  <span className="chip">merchant_category</span>
                  <span className="chip">merchant_city</span>
                </div>
              </div>
              <div style={{ marginBottom: 14 }}>
                <strong>New-customer columns</strong>
                <div className="muted" style={{ fontSize: 12, margin: "2px 0 4px" }}>Used when an ID isn&apos;t in the roster.</div>
                <div className="reasons" style={{ marginTop: 4 }}>
                  <span className="chip">name</span>
                  <span className="chip">stated_income</span>
                  <span className="chip">current_limit</span>
                  <span className="chip">bureau_score</span>
                </div>
              </div>
              <p className="muted" style={{ fontSize: 12, marginTop: 12 }}>
                Headers match common aliases (cif, amt, txn_date, mcc, city…).
                Known IDs attach to the existing customer; any new ID is bootstrapped
                into a fresh customer record so it flows into the cohort sweep.
              </p>
            </div>
            <a className="btn" href={`${API_BASE}/ingest/sample-csv`} download style={{ marginTop: 10, width: "100%", justifyContent: "center" }}>
              <Icon name="download" size={14} /> Download sample CSV
            </a>
          </div>

          <div className="card">
            <h3 style={{ marginBottom: 12 }}>How it works</h3>
            <div className="row" style={{ gap: 10, alignItems: "flex-start", marginBottom: 10 }}>
              <div style={{ width: 24, height: 24, borderRadius: 999, background: "var(--primary-tint)", color: "var(--primary)", display: "grid", placeItems: "center", fontSize: 11, fontWeight: 700, flexShrink: 0 }}>1</div>
              <div style={{ fontSize: 13 }}><strong>Upload + preview</strong><div className="muted" style={{ fontSize: 12 }}>First 10 rows shown for sanity check.</div></div>
            </div>
            <div className="row" style={{ gap: 10, alignItems: "flex-start", marginBottom: 10 }}>
              <div style={{ width: 24, height: 24, borderRadius: 999, background: "var(--primary-tint)", color: "var(--primary)", display: "grid", placeItems: "center", fontSize: 11, fontWeight: 700, flexShrink: 0 }}>2</div>
              <div style={{ fontSize: 13 }}><strong>Ingest</strong><div className="muted" style={{ fontSize: 12 }}>Transaction rows attached to existing customers.</div></div>
            </div>
            <div className="row" style={{ gap: 10, alignItems: "flex-start" }}>
              <div style={{ width: 24, height: 24, borderRadius: 999, background: "var(--primary-tint)", color: "var(--primary)", display: "grid", placeItems: "center", fontSize: 11, fontWeight: 700, flexShrink: 0 }}>3</div>
              <div style={{ fontSize: 13 }}><strong>Run CLR on cohort</strong><div className="muted" style={{ fontSize: 12 }}>Sweep only the uploaded CIFs through L3 decision engine.</div></div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

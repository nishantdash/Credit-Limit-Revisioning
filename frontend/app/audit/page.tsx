import { api, AuditRow } from "../../lib/api";
import { Icon } from "../../components/Icon";
import { MetricCard } from "../../components/MetricCard";
import { Pill } from "../../components/Pill";

const ACTION_VARIANT: Record<string, "green" | "amber" | "red" | "blue" | "purple" | "gray"> = {
  HITL_APPROVED: "green",
  HITL_REJECTED: "red",
  LIMIT_UPDATED: "green",
  LIMIT_UPDATED_AUTO: "green",
  CREATED: "blue",
  CSV_UPLOAD: "purple",
  COHORT_SWEEP_RUN: "purple",
};

export default async function AuditPage() {
  const rows = await api<AuditRow[]>("/analytics/audit-log?limit=200");
  const byType = rows.reduce((acc: Record<string, number>, r) => { acc[r.entity_type] = (acc[r.entity_type] || 0) + 1; return acc; }, {});

  return (
    <>
      <div className="page-head">
        <div>
          <h2 className="page-title">Audit log</h2>
          <p className="page-sub" style={{ marginBottom: 0 }}>Immutable trail of every decision, write-back, and HITL action — RBI/DPDP requirement.</p>
        </div>
        <div className="actions">
          <button className="btn"><Icon name="download" size={14} /> Export</button>
        </div>
      </div>

      <div className="grid cols-4">
        <MetricCard label="Total events" value={rows.length.toString()} sub="Within retention window" iconName="audit" />
        <MetricCard label="Decisions" value={(byType.Decision || 0).toString()} sub="Created + updated" iconName="checklist" />
        <MetricCard label="Card write-backs" value={(byType.Card || 0).toString()} sub="L5 atomic updates" iconName="card" />
        <MetricCard label="Ingestion events" value={(byType.Ingest || 0).toString()} sub="CSV cohort uploads" iconName="upload" />
      </div>

      <div style={{ height: 24 }} />

      <div className="card padless">
        <div className="card-head">
          <div className="input-icon-wrap" style={{ flex: 1, maxWidth: 320 }}>
            <span className="icon"><Icon name="search" size={14} /></span>
            <input placeholder="Search entity or action" />
          </div>
          <div className="row" style={{ gap: 8 }}>
            <button className="btn"><Icon name="filter" size={14} /> All entities <Icon name="chevron-down" size={12} /></button>
            <button className="btn"><Icon name="calendar" size={14} /> All time <Icon name="chevron-down" size={12} /></button>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Entity</th>
                <th>ID</th>
                <th>Action</th>
                <th>Actor</th>
                <th>Payload</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  <td className="muted">{new Date(r.timestamp).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</td>
                  <td><Pill variant="gray" bare>{r.entity_type}</Pill></td>
                  <td className="mono muted">{r.entity_id}</td>
                  <td><Pill variant={ACTION_VARIANT[r.action] || "gray"} bare>{r.action}</Pill></td>
                  <td className="muted">{r.actor}</td>
                  <td><pre className="code" style={{ margin: 0, maxWidth: 480, fontSize: 11 }}>{JSON.stringify(r.payload, null, 2)}</pre></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

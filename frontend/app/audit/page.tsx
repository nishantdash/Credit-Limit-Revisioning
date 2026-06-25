import { api, AuditRow } from "../../lib/api";

export default async function AuditPage() {
  const rows = await api<AuditRow[]>("/analytics/audit-log?limit=200");
  return (
    <>
      <h2>Audit log <span className="layer-badge">L6</span></h2>
      <p className="page-sub">
        Immutable trail of every decision, write-back, and HITL action — RBI/DPDP requirement.
      </p>
      <div className="card" style={{ padding: 0 }}>
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
                <td className="muted">{new Date(r.timestamp).toLocaleString()}</td>
                <td>{r.entity_type}</td>
                <td className="muted">{r.entity_id}</td>
                <td><strong>{r.action}</strong></td>
                <td className="muted">{r.actor}</td>
                <td><pre className="code" style={{ margin: 0, maxWidth: 480 }}>{JSON.stringify(r.payload, null, 2)}</pre></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

import Link from "next/link";
import { api, Customer, inr } from "../../lib/api";

export default async function CustomersPage() {
  const customers = await api<Customer[]>("/customers");
  return (
    <>
      <h2>Customers</h2>
      <p className="page-sub">{customers.length} seeded customers across programmes.</p>
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead>
            <tr>
              <th>CIF</th>
              <th>Name</th>
              <th>Segment</th>
              <th>Programme</th>
              <th>Bureau</th>
              <th>Stated income</th>
              <th>Employment</th>
              <th>DPD 12m</th>
            </tr>
          </thead>
          <tbody>
            {customers.map((c) => (
              <tr key={c.id}>
                <td><Link href={`/customers/${c.id}`}>{c.id}</Link></td>
                <td>{c.name}</td>
                <td><span className={`badge badge-${c.segment}`}>{c.segment}</span></td>
                <td className="muted">{c.programme_id}</td>
                <td>{c.bureau_score}</td>
                <td>{inr(c.stated_income)}</td>
                <td className="muted">{c.employment_type}</td>
                <td style={{ color: c.dpd_max_12m > 60 ? "var(--red)" : c.dpd_max_12m > 0 ? "var(--amber)" : "var(--text-dim)" }}>
                  {c.dpd_max_12m}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

import { api, Customer } from "../../lib/api";
import { TriggerSimulator } from "./TriggerSimulator";
import { Icon } from "../../components/Icon";

export default async function TriggersPage() {
  const customers = await api<Customer[]>("/customers");
  return (
    <>
      <div className="page-head">
        <div>
          <h2 className="page-title">Trigger engine</h2>
          <p className="page-sub" style={{ marginBottom: 0 }}>
            Fire an event into CLR, or run a continuous micro-review across the whole book (§7.2).
          </p>
        </div>
      </div>

      <div className="banner" style={{ marginBottom: 24 }}>
        <Icon name="info" size={18} />
        <div>
          <span className="banner-title">Event-driven, not end-of-day batch.</span>{" "}
          Salary credits, declined high-value transactions, utilisation thresholds and AA pushes each trigger a
          decision. The micro-review sweep replaces the quarterly batch with continuous re-scoring.
        </div>
      </div>

      <TriggerSimulator customers={customers} />
    </>
  );
}

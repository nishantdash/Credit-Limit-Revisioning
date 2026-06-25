import { api, Customer } from "../../lib/api";
import { TriggerSimulator } from "./TriggerSimulator";
import { Icon } from "../../components/Icon";

export default async function TriggersPage() {
  const customers = await api<Customer[]>("/customers");
  return (
    <>
      <div className="page-head">
        <div>
          <h2 className="page-title">Trigger simulator</h2>
          <p className="page-sub" style={{ marginBottom: 0 }}>
            Fire a Hyperface event into CLR, or run a periodic sweep across the entire customer book.
          </p>
        </div>
      </div>

      <div className="banner" style={{ marginBottom: 24 }}>
        <Icon name="info" size={18} />
        <div>
          <span className="banner-title">Three trigger modes per the spec.</span>{" "}
          Event-driven fires on a specific transaction event (utilisation, spike). Periodic sweeps run the whole book. Income step-change fires when the L2b estimator detects a real cashflow shift.
        </div>
      </div>

      <TriggerSimulator customers={customers} />
    </>
  );
}

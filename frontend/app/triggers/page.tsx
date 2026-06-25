import { api, Customer } from "../../lib/api";
import { TriggerSimulator } from "./TriggerSimulator";

export default async function TriggersPage() {
  const customers = await api<Customer[]>("/customers");
  return (
    <>
      <h2>Trigger simulator <span className="layer-badge">L3</span></h2>
      <p className="page-sub">
        Fire a Hyperface event into CLR (utilisation threshold, spend spike, income step-change),
        or run a periodic sweep over the entire customer book.
      </p>
      <TriggerSimulator customers={customers} />
    </>
  );
}

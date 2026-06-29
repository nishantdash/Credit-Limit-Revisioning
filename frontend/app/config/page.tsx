import { api, TenantConfig } from "../../lib/api";
import { ConfigClient } from "./ConfigClient";

export default async function ConfigPage() {
  const presets = await api<TenantConfig[]>("/config/presets");
  return (
    <>
      <div className="page-head">
        <div>
          <h2 className="page-title">Tenant configuration</h2>
          <p className="page-sub" style={{ marginBottom: 0 }}>
            One codebase, deployed per tenant — everything that encodes risk appetite is externalised here (§8).
            Switch the active archetype to re-run the same engine with a different policy.
          </p>
        </div>
      </div>
      <ConfigClient presets={presets} />
    </>
  );
}

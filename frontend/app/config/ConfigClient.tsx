"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, TenantConfig } from "../../lib/api";
import { Icon } from "../../components/Icon";
import { Pill } from "../../components/Pill";

const ARCHE_SUB: Record<string, string> = {
  BANK: "Balanced, capital-optimising · tight guardrails",
  NBFC: "Growth-led, higher yield · wider bands",
  SFB: "Inclusion-led, thin-file · strong distress watch",
};

const KNOBS: { key: string; label: string; fmt: (v: unknown) => string }[] = [
  { key: "max_dti", label: "Max DTI (capacity cap)", fmt: (v) => `${(Number(v) * 100).toFixed(0)}%` },
  { key: "decrease_buffer_pct", label: "Decrease buffer", fmt: (v) => `${(Number(v) * 100).toFixed(0)}%` },
  { key: "increase_frequency_gate_months", label: "Increase frequency gate", fmt: (v) => `${v} months` },
  { key: "per_customer_leverage_ceiling_pct", label: "Per-customer leverage ceiling", fmt: (v) => `${(Number(v) * 100).toFixed(0)}%` },
  { key: "portfolio_increase_velocity_cap_pct", label: "Portfolio increase-velocity cap", fmt: (v) => `${(Number(v) * 100).toFixed(0)}%` },
  { key: "auto_offer_min_confidence", label: "Auto-offer confidence floor", fmt: (v) => `${(Number(v) * 100).toFixed(0)}%` },
  { key: "cautious_increase_pct", label: "Tier-3 cautious increase", fmt: (v) => `${(Number(v) * 100).toFixed(0)}%` },
  { key: "network_enabled", label: "Network layer (positive-only)", fmt: (v) => (v ? "Enabled" : "Disabled") },
  { key: "consent_channel", label: "Consent channel", fmt: (v) => String(v) },
];

export function ConfigClient({ presets }: { presets: TenantConfig[] }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const active = presets.find((p) => p.active) ?? presets[0];

  async function activate(archetype: string) {
    setBusy(true);
    try {
      await api("/config/activate", { method: "POST", body: JSON.stringify({ archetype }) });
      router.refresh();
    } catch (e) {
      alert(`Failed: ${e}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="arche">
        {presets.map((p) => (
          <button key={p.archetype} className={`arche-card ${p.active ? "active" : ""}`} disabled={busy} onClick={() => activate(p.archetype)}>
            <div className="row-between" style={{ marginBottom: 8 }}>
              <Pill variant={p.archetype === "BANK" ? "blue" : p.archetype === "NBFC" ? "teal" : "purple"} bare>{p.archetype}</Pill>
              {p.active && <Pill variant="green" bare>Active</Pill>}
            </div>
            <div className="a-name">{p.name}</div>
            <div className="a-sub">{ARCHE_SUB[p.archetype]}</div>
          </button>
        ))}
      </div>

      <div style={{ height: 24 }} />

      <div className="banner" style={{ marginBottom: 20 }}>
        <Icon name="info" size={18} />
        <div>
          <span className="banner-title">Switching the archetype re-parameterises the live engine.</span>{" "}
          Re-run a micro-review sweep afterwards to see the same customers decided under the new policy — e.g. a Tier 1
          growth offer widens from +50% (Bank) to +60% (NBFC).
        </div>
      </div>

      <div className="card padless">
        <div className="card-head">
          <h3>Active policy · {active.name}</h3>
          <span className="muted" style={{ fontSize: 12 }}>externalised — no code change</span>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Parameter</th><th>Value</th><th>Section</th></tr></thead>
            <tbody>
              {KNOBS.map((k) => (
                <tr key={k.key}>
                  <td>{k.label}</td>
                  <td><strong>{active.config[k.key] !== undefined ? k.fmt(active.config[k.key]) : "—"}</strong></td>
                  <td className="muted" style={{ fontSize: 12 }}>{sectionFor(k.key)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

function sectionFor(key: string): string {
  if (key.includes("dti") || key.includes("buffer") || key.includes("cautious")) return "§5 formulas";
  if (key.includes("frequency") || key.includes("leverage") || key.includes("velocity")) return "§5.4 anti-spiral";
  if (key.includes("confidence")) return "§3.3 gating";
  if (key.includes("network")) return "§2.4 network";
  if (key.includes("consent")) return "§6 consent";
  return "§8 config";
}

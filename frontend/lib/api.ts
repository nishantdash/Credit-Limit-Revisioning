const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`API ${path} ${res.status}: ${txt}`);
  }
  return res.json() as Promise<T>;
}

export async function uploadFile<T>(path: string, file: File): Promise<T> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${BASE}${path}`, { method: "POST", body: fd });
  if (!res.ok) throw new Error(`Upload ${path} ${res.status}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

export const API_BASE = BASE;

// ── Types ────────────────────────────────────────────────────────────────────

export type Customer = {
  id: string;
  name: string;
  entity_type: "RETAIL" | "MSME";
  segment: string;
  employment_type: string;
  programme_id: string;
  bureau_score: number;
  dpd_max_12m: number;
  account_vintage_months: number;
  stated_income: number;
  external_debt: number;
  fraud_flag: boolean;
  legal_block_flag: boolean;
  aa_consent_active: boolean;
  trade_dpd_days: number | null;
  dscr: number | null;
  working_capital_utilization: number | null;
};

export type Card = {
  id: string;
  customer_id: string;
  current_limit: number;
  outstanding: number;
  statement_balance: number;
  last_payment: number;
  min_due_last: number;
  peak_drawn_12m: number;
  months_since_last_change: number;
  months_inactive: number;
};

export type Intent = "GROWTH" | "DISTRESS" | "SEASONAL" | "NEUTRAL" | "KNOCKOUT";
export type Direction = "INCREASE" | "DECREASE" | "MAINTAIN" | "FREEZE";
export type Pipeline = "OFFER" | "ACTION" | "NONE";

export type Decision = {
  id: string;
  customer_id: string;
  card_id: string;
  created_at: string;
  trigger_type: string;
  entity_type: string;
  tenant_archetype: string;
  risk_tier: number;
  pd_pre: number;
  pd_post_projected: number;
  intent: Intent;
  intent_confidence: number;
  matrix_cell: string;
  direction: Direction;
  magnitude_pct: number;
  duration: "PERMANENT" | "TEMPORARY" | "NA";
  confidence: number;
  auto_revert_at: string | null;
  current_limit: number;
  recommended_limit: number;
  income_estimate: number;
  external_debt: number;
  capacity_headroom: number;
  reason_codes: string[];
  knockouts: string[];
  applied_caps: string[];
  signal_snapshot: Record<string, Record<string, unknown>>;
  explainer_officer: string;
  explainer_customer: string;
  consent_copy: string;
  pipeline: Pipeline;
  consent_status: "NA" | "PENDING_CONSENT" | "ACCEPTED" | "DECLINED";
  consent_channel: string | null;
  consent_decided_at: string | null;
  review_required: boolean;
  review_status: "NA" | "PENDING" | "APPROVED" | "REJECTED";
  review_by: string | null;
  review_at: string | null;
  executed: boolean;
  executed_at: string | null;
  customer_notified: boolean;
};

export type Funnel = {
  customers: number;
  reviewed: number;
  by_intent: Record<string, number>;
  by_tier: Record<string, number>;
  by_direction: Record<string, number>;
  offers_pending_consent: number;
  offers_accepted: number;
  actions_applied: number;
  review_pending: number;
  knockouts: number;
};

export type Roi = {
  offered_uplift_inr: number;
  activated_uplift_inr: number;
  exposure_reduced_inr: number;
  avg_pd_pre: number;
  avg_pd_post: number;
  increases: number;
  decreases: number;
  temporary_offers: number;
  estimated_incremental_interchange_monthly_inr: number;
};

export type Guardrails = {
  portfolio_increase_cap_pct: number;
  portfolio_increase_used_pct: number;
  portfolio_headroom_pct: number;
  total_book_limit_inr: number;
  increase_extended_30d_inr: number;
  decisions_capped: number;
  cap_breakdown: Record<string, number>;
};

export type TenantConfig = {
  id: number;
  name: string;
  archetype: "BANK" | "NBFC" | "SFB";
  active: boolean;
  config: Record<string, number | string | boolean | object>;
  updated_at: string;
};

export type AuditRow = {
  timestamp: string;
  entity_type: string;
  entity_id: string;
  action: string;
  actor: string;
  payload: Record<string, unknown> | null;
};

export type IngestSummary = {
  rows_total: number;
  rows_with_txn_data: number;
  transactions_ingested: number;
  cohort_customer_ids: string[];
  known_customer_ids: string[];
  created_customer_ids: string[];
  unknown_customer_ids: string[];
  errors: string[];
};

export type CohortSweepResponse = {
  requested: number;
  swept: number;
  skipped_unknown: string[];
  decisions: Decision[];
};

// ── Formatting + label helpers ───────────────────────────────────────────────

export function inr(value: number): string {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value);
}

export function inrCompact(value: number): string {
  if (Math.abs(value) >= 1e7) return `₹${(value / 1e7).toFixed(2)}Cr`;
  if (Math.abs(value) >= 1e5) return `₹${(value / 1e5).toFixed(2)}L`;
  return inr(value);
}

export function pct(value: number, digits = 2): string {
  return `${(value * 100).toFixed(digits)}%`;
}

export const TIER_LABEL: Record<number, string> = {
  1: "Tier 1 · Elite",
  2: "Tier 2 · Prime",
  3: "Tier 3 · Subprime",
  4: "Tier 4 · Critical",
};

export const INTENT_VARIANT: Record<string, "green" | "red" | "orange" | "gray" | "purple"> = {
  GROWTH: "green",
  DISTRESS: "red",
  SEASONAL: "orange",
  NEUTRAL: "gray",
  KNOCKOUT: "purple",
};

export const DIRECTION_VARIANT: Record<string, "green" | "red" | "gray" | "amber"> = {
  INCREASE: "green",
  DECREASE: "red",
  MAINTAIN: "gray",
  FREEZE: "amber",
};

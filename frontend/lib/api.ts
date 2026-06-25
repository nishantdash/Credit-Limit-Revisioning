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

export type Customer = {
  id: string;
  name: string;
  segment: string;
  bureau_score: number;
  programme_id: string;
  dpd_max_12m: number;
  stated_income: number;
  employment_type: string;
};

export type Card = {
  id: string;
  customer_id: string;
  current_limit: number;
  current_balance: number;
  benefits_tier: string;
  months_at_current_limit: number;
};

export type Decision = {
  id: string;
  customer_id: string;
  card_id: string;
  created_at: string;
  current_limit: number;
  recommended_limit: number;
  decision: "UPGRADE" | "DOWNGRADE" | "FREEZE";
  confidence: number;
  pd_pre: number;
  pd_post_projected: number;
  income_estimate: number;
  behavioral_score: number;
  reason_codes: string[];
  explainer_text_officer: string;
  explainer_text_customer: string;
  trigger_type: string;
  hitl_required: boolean;
  hitl_status: string;
  hitl_decided_by: string | null;
  hitl_decided_at: string | null;
  benefits_tier_from: string | null;
  benefits_tier_to: string | null;
  executed: boolean;
  executed_at: string | null;
  customer_notified: boolean;
  customer_accepted: boolean | null;
};

export type Funnel = {
  eligible: number;
  reviewed: number;
  upgrade_recommended: number;
  downgrade_recommended: number;
  freeze_recommended: number;
  hitl_pending: number;
  executed: number;
  customer_notified: number;
  customer_accepted: number;
};

export type Roi = {
  total_limit_uplift_inr: number;
  avg_pd_pre: number;
  avg_pd_post: number;
  upgrades_count: number;
  downgrades_count: number;
  benefits_tier_upgrades: number;
  estimated_incremental_interchange_monthly_inr: number;
};

export type AuditRow = {
  timestamp: string;
  entity_type: string;
  entity_id: string;
  action: string;
  actor: string;
  payload: Record<string, unknown> | null;
};

export function inr(value: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

export function pct(value: number, digits = 2): string {
  return `${(value * 100).toFixed(digits)}%`;
}

export type IngestSummary = {
  rows_total: number;
  rows_with_txn_data: number;
  transactions_ingested: number;
  cohort_customer_ids: string[];
  known_customer_ids: string[];
  unknown_customer_ids: string[];
  errors: string[];
};

export type CohortSweepResponse = {
  requested: number;
  swept: number;
  skipped_unknown: string[];
  decisions: Decision[];
};

export async function uploadFile<T>(path: string, file: File): Promise<T> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${BASE}${path}`, { method: "POST", body: fd });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Upload ${path} ${res.status}: ${txt}`);
  }
  return res.json() as Promise<T>;
}

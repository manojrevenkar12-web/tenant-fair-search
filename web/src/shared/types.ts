/** The shape of reports/dev.json and reports/heldout.json, written by tfs.eval. */
export type Shape = "keyword" | "sentence" | "agent" | "sku";

export type DesignResult = {
  queries: number;
  ndcg: number;
  ndcg_ci: [number, number];
  by_shape: Partial<Record<Shape, number>>;
  sku_first: number | null;
  first_ok: number | null;
  violations_top10: number;
  zero_results: number;
  es_ms: number;
  cost_per_1000_eur: number;
  plans: Record<string, number>;
};

export type Side = {
  quiet_calm_p50_ms: number;
  quiet_calm_p99_ms: number;
  quiet_burst_p50_ms: number;
  quiet_burst_p99_ms: number;
  quiet_burst_failed: number;
  noisy_limited_share: number;
  noisy_failed_share: number;
  noisy_served_in_burst: number;
  noisy_sent_in_burst: number;
};

export type Listing = { title: string; price: number; grade: number };

export type Example = {
  tenant: string;
  shape: Shape;
  query: string;
  filters: Record<string, unknown> | null;
  understood: { text: string; filters: Record<string, unknown> };
  plan: string;
  lexical: { ndcg: number; top: Listing[] };
  routed: { ndcg: number; top: Listing[] };
};

export type Report = {
  seeds: number[];
  tenants: string[];
  products: number;
  queries_per_seed: number;
  shapes: Record<Shape, number>;
  designs: Record<string, DesignResult>;
  comparisons: Record<string, { mean: number; ci: [number, number]; n: number }>;
  load: null | { capacity_qps: number; seeds: number; fair: Side; none: Side };
  examples: Example[];
};

export type Hit = { id: string; score: number };
export type SearchAnswer = {
  tenant: string;
  design: string;
  shape: string;
  plan: string;
  text: string;
  filters: Record<string, unknown>;
  hits: Hit[];
  esTookMs: number;
  costEur: number;
};

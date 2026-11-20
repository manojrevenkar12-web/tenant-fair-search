export const pct = (v: number | null | undefined, digits = 1) => (v == null ? "n/a" : `${(v * 100).toFixed(digits)}%`);
export const ms = (v: number) => `${v >= 100 ? Math.round(v).toLocaleString("en") : v.toFixed(v < 10 ? 1 : 0)} ms`;
export const num = (v: number, digits = 3) => v.toFixed(digits);
export const eur = (v: number) => `€${v.toFixed(v < 0.01 ? 5 : 3)}`;

export const DESIGN_LABEL: Record<string, string> = {
  lexical: "Lexical (BM25) only",
  semantic: "Vector only",
  hybrid_rrf: "Hybrid, fused, every query",
  hybrid_with_understanding: "Hybrid + query understanding",
  routed_without_understanding: "Routed, no understanding",
  routed: "Routed + query understanding",
};

export const SHAPE_LABEL: Record<string, string> = {
  keyword: "Keywords",
  sentence: "Full sentences",
  agent: "AI agents",
  sku: "SKU lookups",
};

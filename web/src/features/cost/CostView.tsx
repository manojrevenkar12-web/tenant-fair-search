import { DESIGN_LABEL, eur, ms, pct } from "../../shared/format";
import { useReport } from "../../shared/data";
import { Bars } from "../../shared/ui/Bars";
import { Empty, ErrorState, Loading } from "../../shared/ui/states";
import { color } from "../../theme/tokens";

const TONE: Record<string, string> = { routed: color.routed, lexical: color.lexical, semantic: color.semantic, hybrid_rrf: color.hybrid };

export function CostView() {
  const { data, error, loading, retry } = useReport("dev");
  if (loading) return <Loading label="Loading the cost report" />;
  if (error) return error.status === 404 ? <Empty title="No evaluation yet">Run the evaluate workflow first.</Empty> : <ErrorState error={error} retry={retry} />;
  if (!data) return null;
  const names = Object.keys(TONE).filter((n) => data.designs[n]);
  const max = Math.max(...names.map((n) => data.designs[n]?.es_ms ?? 0));
  const routed = data.designs.routed;
  const plans = routed ? Object.entries(routed.plans) : [];
  const total = plans.reduce((a, [, v]) => a + v, 0);
  return (
    <div className="space-y-8">
      <section>
        <h1 className="max-w-[24ch] text-hero font-bold">What a query costs</h1>
        <p className="mt-3 max-w-prose text-lead text-muted">
          Cluster time is what Elasticsearch reports for each request. Routing skips the vector search for SKU lookups and for words the shop's model has never seen, so it
          spends less than fusing every query.
        </p>
      </section>
      <section className="max-w-[48rem]">
        <h2 className="mb-3 text-title font-bold">Cluster time per query</h2>
        <Bars
          caption="Cluster milliseconds per query by design"
          max={max}
          bars={names.map((n) => ({ key: n, label: DESIGN_LABEL[n] ?? n, value: data.designs[n]?.es_ms ?? 0, color: TONE[n] ?? color.muted, text: ms(data.designs[n]?.es_ms ?? 0) }))}
        />
        <p className="mt-3 text-small text-muted">
          Per 1,000 queries: {names.map((n) => `${DESIGN_LABEL[n]} ${eur(data.designs[n]?.cost_per_1000_eur ?? 0)}`).join(" · ")}
        </p>
      </section>
      <section className="max-w-[48rem]">
        <h2 className="mb-3 text-title font-bold">How the routed design answered</h2>
        <ul className="divide-y divide-line border-y border-line">
          {plans.map(([p, v]) => (
            <li key={p} className="flex justify-between py-2">
              <span>{p}</span>
              <span className="font-semibold text-ink">{pct(v / total)}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

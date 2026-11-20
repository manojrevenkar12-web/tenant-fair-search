import { DESIGN_LABEL, SHAPE_LABEL, eur, ms, num, pct } from "../../shared/format";
import { useReport } from "../../shared/data";
import type { Report, Shape } from "../../shared/types";
import { Bars } from "../../shared/ui/Bars";
import { Empty, ErrorState, Loading } from "../../shared/ui/states";
import { color } from "../../theme/tokens";
import { ExampleCompare } from "./ExampleCompare";

const SERIES: [string, string][] = [
  ["routed", color.routed],
  ["lexical", color.lexical],
  ["semantic", color.semantic],
  ["hybrid_rrf", color.hybrid],
];

function ShapeBars({ rep }: { rep: Report }) {
  const shapes = (Object.keys(SHAPE_LABEL) as Shape[]).filter((s) => rep.designs.routed?.by_shape[s] != null);
  return (
    <div className="grid gap-6 md:grid-cols-2">
      {shapes.map((s) => (
        <div key={s}>
          <h3 className="mb-2 text-body font-semibold">
            {SHAPE_LABEL[s]} <span className="font-normal text-muted">· {rep.shapes[s]} a world</span>
          </h3>
          <Bars
            caption={`nDCG@10 for ${SHAPE_LABEL[s]}`}
            max={1}
            bars={SERIES.filter(([d]) => rep.designs[d]).map(([d, c]) => {
              const v = rep.designs[d]?.by_shape[s] ?? 0;
              return { key: d, label: DESIGN_LABEL[d] ?? d, value: v, color: c, text: num(v, 3) };
            })}
          />
        </div>
      ))}
    </div>
  );
}

function DesignTable({ rep }: { rep: Report }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[46rem] text-left">
        <thead className="text-small text-muted">
          <tr className="border-b border-line">
            <th className="py-2 font-semibold">Design</th>
            <th className="py-2 text-right font-semibold">nDCG@10</th>
            <th className="py-2 text-right font-semibold">95% interval</th>
            <th className="py-2 text-right font-semibold">SKU first</th>
            <th className="py-2 text-right font-semibold">Constraint breaks</th>
            <th className="py-2 text-right font-semibold">Cluster time</th>
            <th className="py-2 text-right font-semibold">Per 1,000</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(rep.designs).map(([name, d]) => (
            <tr key={name} className={`border-b border-line ${name === "routed" ? "font-semibold text-ink" : ""}`}>
              <td className="py-2">{DESIGN_LABEL[name] ?? name}</td>
              <td className="py-2 text-right">{num(d.ndcg)}</td>
              <td className="py-2 text-right text-muted">
                {num(d.ndcg_ci[0])} to {num(d.ndcg_ci[1])}
              </td>
              <td className="py-2 text-right">{pct(d.sku_first)}</td>
              <td className="py-2 text-right">{pct(d.violations_top10)}</td>
              <td className="py-2 text-right">{ms(d.es_ms)}</td>
              <td className="py-2 text-right">{eur(d.cost_per_1000_eur)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function RelevanceView() {
  const { data, error, loading, retry } = useReport("dev");
  if (loading) return <Loading label="Loading the relevance report" rows={8} />;
  if (error) return error.status === 404 ? <Empty title="No evaluation yet">Run the evaluate workflow to generate reports/dev.json.</Empty> : <ErrorState error={error} retry={retry} />;
  if (!data) return null;
  const routed = data.designs.routed;
  const lexical = data.designs.lexical;
  return (
    <div className="space-y-8">
      <section>
        <h1 className="max-w-[24ch] text-hero font-bold">Same query, two answers</h1>
        <p className="mt-3 max-w-prose text-lead text-muted">
          Routed search with query understanding scores <b className="text-ink">{num(routed?.ndcg ?? 0)}</b> nDCG@10 against{" "}
          {num(lexical?.ndcg ?? 0)} for lexical search, over {(data.queries_per_seed * data.seeds.length).toLocaleString("en")} graded queries on{" "}
          {data.seeds.length} simulated worlds.
        </p>
        <div className="mt-6">
          {data.examples.length > 0 ? <ExampleCompare examples={data.examples} /> : <Empty title="No examples in this report">The evaluation keeps examples from its first world.</Empty>}
        </div>
      </section>
      <section>
        <h2 className="mb-4 text-title font-bold">By query shape</h2>
        <ShapeBars rep={data} />
      </section>
      <section>
        <h2 className="mb-4 text-title font-bold">Every design on the same queries</h2>
        <DesignTable rep={data} />
      </section>
    </div>
  );
}

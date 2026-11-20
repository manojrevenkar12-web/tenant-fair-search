import { ms, pct } from "../../shared/format";
import { useReport } from "../../shared/data";
import type { Side } from "../../shared/types";
import { Bars } from "../../shared/ui/Bars";
import { Empty, ErrorState, Loading } from "../../shared/ui/states";
import { color } from "../../theme/tokens";

const ROWS: { key: keyof Side; label: string; kind: "ms" | "pct" }[] = [
  { key: "quiet_calm_p99_ms", label: "Other shops' p99, before the burst", kind: "ms" },
  { key: "quiet_burst_p50_ms", label: "Other shops' p50, during the burst", kind: "ms" },
  { key: "quiet_burst_p99_ms", label: "Other shops' p99, during the burst", kind: "ms" },
  { key: "quiet_burst_failed", label: "Other shops' searches that failed", kind: "pct" },
  { key: "noisy_limited_share", label: "Agent's searches told to retry later (429)", kind: "pct" },
  { key: "noisy_failed_share", label: "Agent's searches that timed out", kind: "pct" },
];

export function IsolationView() {
  const { data, error, loading, retry } = useReport("dev");
  if (loading) return <Loading label="Loading the isolation report" />;
  if (error) return error.status === 404 ? <Empty title="No evaluation yet">Run the evaluate workflow first.</Empty> : <ErrorState error={error} retry={retry} />;
  const load = data?.load;
  if (!load) return <Empty title="This report has no load test">The evaluation runs one with every world.</Empty>;
  const p99 = [
    { key: "fair", label: "Per-tenant admission", value: load.fair.quiet_burst_p99_ms, color: color.fair, text: ms(load.fair.quiet_burst_p99_ms) },
    { key: "none", label: "One shared queue", value: load.none.quiet_burst_p99_ms, color: color.none, text: ms(load.none.quiet_burst_p99_ms) },
  ];
  return (
    <div className="space-y-8">
      <section>
        <h1 className="max-w-[26ch] text-hero font-bold">One shop's agent bursts. The others don't notice.</h1>
        <p className="mt-3 max-w-prose text-lead text-muted">
          The service and a one-node cluster handled about <b className="text-ink">{Math.round(load.capacity_qps)} searches a second</b> on the CI runner. One shop's AI
          agent then sent 1.6 times that for 14 seconds while three other shops kept searching. The same arrivals were played against both admission modes.
        </p>
      </section>
      <section className="max-w-[48rem]">
        <h2 className="mb-3 text-title font-bold">Other shops' slowest searches during the burst</h2>
        <Bars bars={p99} max={Math.max(...p99.map((b) => b.value))} caption="p99 latency of the other shops during the burst" />
      </section>
      <section className="max-w-[48rem] overflow-x-auto">
        <table className="w-full text-left">
          <thead className="text-small text-muted">
            <tr className="border-b border-line">
              <th className="py-2 font-semibold">Averaged over {load.seeds} worlds</th>
              <th className="py-2 text-right font-semibold">Per-tenant admission</th>
              <th className="py-2 text-right font-semibold">One shared queue</th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((r) => {
              const f = load.fair[r.key];
              const n = load.none[r.key];
              const fmt = (v: number) => (r.kind === "ms" ? ms(v) : pct(v));
              return (
                <tr key={r.key} className="border-b border-line">
                  <td className="py-2">{r.label}</td>
                  <td className="py-2 text-right font-semibold text-ink">{fmt(f)}</td>
                  <td className="py-2 text-right">{fmt(n)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </div>
  );
}

import { AnimatePresence, motion } from "framer-motion";
import { type FormEvent, useState } from "react";
import { type Problem, search } from "../../shared/data";
import type { SearchAnswer } from "../../shared/types";
import { Empty, ErrorState } from "../../shared/ui/states";
import { motion as m } from "../../theme/motion";

const TENANTS = ["outdoor", "fashion", "parts", "home"];
const SAMPLES = ["navy raincoat", "looking for a warm puffer for winter trips under 200 euros", "OD-26488", "jubilee clip stainless"];

/** Live search against a running service. The evaluation has trained and indexed the shops first. */
export function SearchView() {
  const [tenant, setTenant] = useState("outdoor");
  const [query, setQuery] = useState(SAMPLES[0] ?? "");
  const [state, setState] = useState<{ loading: boolean; error: Problem | null; answer: SearchAnswer | null }>({ loading: false, error: null, answer: null });

  const run = async (e?: FormEvent) => {
    e?.preventDefault();
    if (!query.trim()) return;
    setState({ loading: true, error: null, answer: null });
    try {
      setState({ loading: false, error: null, answer: await search(tenant, query, null) });
    } catch (err) {
      setState({ loading: false, error: err as Problem, answer: null });
    }
  };

  const a = state.answer;
  const constraints = a ? Object.entries(a.filters).filter(([, v]) => v != null) : [];
  return (
    <div className="max-w-[52rem] space-y-6">
      <section>
        <h1 className="text-hero font-bold">Try a search</h1>
        <p className="mt-3 max-w-prose text-lead text-muted">Runs against your local service. The answer shows how the query was understood and which plan ran.</p>
      </section>
      <form onSubmit={run} className="flex flex-wrap items-end gap-3 rounded-card border border-line bg-sheet p-4">
        <label className="flex flex-col text-small font-semibold text-ink">
          Shop
          <select value={tenant} onChange={(e) => setTenant(e.target.value)} className="mt-1 rounded-soft border border-line bg-sheet px-3 py-2 text-body font-normal">
            {TENANTS.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        </label>
        <label className="flex min-w-[18rem] flex-1 flex-col text-small font-semibold text-ink">
          Query
          <input value={query} onChange={(e) => setQuery(e.target.value)} className="mt-1 rounded-soft border border-line px-3 py-2 text-body font-normal" />
        </label>
        <button type="submit" disabled={state.loading} className="rounded-soft bg-focus px-5 py-2 font-semibold text-sheet disabled:opacity-60">
          {state.loading ? "Searching" : "Search"}
        </button>
      </form>
      <div className="flex flex-wrap gap-2 text-small">
        {SAMPLES.map((s) => (
          <button key={s} type="button" onClick={() => setQuery(s)} className="rounded-pill border border-line bg-sheet px-3 py-1 text-muted hover:text-ink">
            {s}
          </button>
        ))}
      </div>
      {state.loading && (
        <div role="status" aria-label="Searching" className="animate-pulse space-y-2">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-8 rounded-soft bg-line" />
          ))}
        </div>
      )}
      {state.error && <ErrorState error={state.error} retry={() => void run()} />}
      {a && a.hits.length === 0 && <Empty title="No products matched">Try fewer constraints, or another shop: each shop has its own catalogue.</Empty>}
      {a && a.hits.length > 0 && (
        <section aria-label="Results" className="rounded-card border border-line bg-sheet p-5">
          <p className="text-small text-muted">
            {a.shape} query · <b className="text-ink">{a.plan}</b> plan · {a.esTookMs} ms in the cluster
            {constraints.length > 0 && <> · filters {constraints.map(([k, v]) => `${k} ${String(v)}`).join(", ")}</>}
          </p>
          <ol className="mt-3 divide-y divide-line">
            <AnimatePresence>
              {a.hits.map((h, i) => (
                <motion.li key={h.id} className="flex justify-between py-2" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * m.stagger, duration: m.settle }}>
                  <span>
                    <span className="mr-3 text-muted">{i + 1}</span>
                    {h.id}
                  </span>
                  <span className="text-small text-muted">{h.score.toFixed(4)}</span>
                </motion.li>
              ))}
            </AnimatePresence>
          </ol>
        </section>
      )}
    </div>
  );
}

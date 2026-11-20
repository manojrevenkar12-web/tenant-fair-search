import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";
import { DESIGN_LABEL, SHAPE_LABEL, num } from "../../shared/format";
import type { Example, Listing } from "../../shared/types";
import { Grade, GradeKey } from "../../shared/ui/Grade";
import { motion as m } from "../../theme/motion";

function Column({ title, ndcg, top, tone }: { title: string; ndcg: number; top: Listing[]; tone: string }) {
  return (
    <section aria-label={title} className="min-w-0">
      <div className="flex items-baseline justify-between border-b-rule pb-2" style={{ borderColor: tone }}>
        <h3 className="text-body font-semibold">{title}</h3>
        <span className="text-small text-muted">
          nDCG@10 <b className="text-ink">{num(ndcg, 2)}</b>
        </span>
      </div>
      <ol className="divide-y divide-line">
        {top.map((l, i) => (
          <motion.li
            key={`${title}-${i}-${l.title}`}
            className="flex items-center gap-3 py-2"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: m.settle, delay: i * m.stagger, ease: m.ease }}
          >
            <span className="w-5 text-right text-small text-muted">{i + 1}</span>
            <Grade value={l.grade} />
            <span className="min-w-0 flex-1 truncate text-copy">{l.title}</span>
            <span className="text-small text-muted">€{l.price.toFixed(2)}</span>
          </motion.li>
        ))}
        {top.length === 0 && <li className="py-3 text-muted">No results.</li>}
      </ol>
    </section>
  );
}

/** The hero: one real query from the evaluation, answered by lexical search and by the routed design. */
export function ExampleCompare({ examples }: { examples: Example[] }) {
  const [i, setI] = useState(0);
  const ex = examples[Math.min(i, examples.length - 1)];
  if (!ex) return null;
  const constraints = Object.entries(ex.understood.filters);
  return (
    <div>
      <div role="tablist" aria-label="Query shape" className="mb-4 flex flex-wrap gap-2">
        {examples.map((e, j) => (
          <button
            key={e.shape}
            role="tab"
            type="button"
            aria-selected={j === i}
            onClick={() => setI(j)}
            className={`rounded-pill border px-3 py-1 text-small font-semibold ${j === i ? "border-focus bg-focusWash text-ink" : "border-line bg-sheet text-muted hover:text-ink"}`}
          >
            {SHAPE_LABEL[e.shape]}
          </button>
        ))}
      </div>
      <AnimatePresence mode="wait">
        <motion.div key={ex.query} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: m.quick }}>
          <div className="rounded-card border border-line bg-sheet p-5">
            <p className="text-small text-muted">
              {ex.tenant} shop · {ex.filters ? "an AI agent sent" : "a shopper typed"}
            </p>
            <p className="mt-1 text-lead font-semibold text-ink">
              “{ex.query}”{ex.filters && <span className="font-normal text-muted"> with fields {JSON.stringify(ex.filters)}</span>}
            </p>
            <p className="mt-2 text-small text-muted">
              Understood as <b className="text-ink">{ex.plan}</b> search for “{ex.understood.text || "everything"}”
              {constraints.length > 0 && <> with {constraints.map(([k, v]) => `${k} ${String(v)}`).join(", ")}</>}
            </p>
            <div className="mt-5 grid gap-6 md:grid-cols-2">
              <Column title={DESIGN_LABEL.lexical ?? "Lexical"} ndcg={ex.lexical.ndcg} top={ex.lexical.top} tone="#eb6834" />
              <Column title={DESIGN_LABEL.routed ?? "Routed"} ndcg={ex.routed.ndcg} top={ex.routed.top} tone="#2a78d6" />
            </div>
          </div>
        </motion.div>
      </AnimatePresence>
      <div className="mt-3">
        <GradeKey />
      </div>
    </div>
  );
}

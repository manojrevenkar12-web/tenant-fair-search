import { CostView } from "./features/cost/CostView";
import { IsolationView } from "./features/isolation/IsolationView";
import { RelevanceView } from "./features/relevance/RelevanceView";
import { SearchView } from "./features/search/SearchView";
import { type View, go, useRoute } from "./shared/route";

const TABS: { view: View; label: string }[] = [
  { view: "relevance", label: "Relevance" },
  { view: "isolation", label: "Tenant isolation" },
  { view: "cost", label: "Cost per query" },
  { view: "search", label: "Try a search" },
];

export function App() {
  const view = useRoute();
  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-sheet">
        <div className="mx-auto flex max-w-page flex-wrap items-end justify-between gap-4 px-6 pt-5">
          <div className="pb-4">
            <p className="text-lead font-bold text-ink">Tenant-fair search</p>
            <p className="text-small text-muted">Hybrid product search for many shops on one cluster, measured on simulated catalogues</p>
          </div>
          <nav aria-label="Views" className="flex flex-wrap gap-1">
            {TABS.map((t) => (
              <button
                key={t.view}
                type="button"
                onClick={() => go(t.view)}
                aria-current={view === t.view ? "page" : undefined}
                className={`border-b-rule px-3 pb-3 pt-2 font-semibold transition-colors ${view === t.view ? "border-focus text-ink" : "border-transparent text-muted hover:text-ink"}`}
              >
                {t.label}
              </button>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-page px-6 py-7">
        {view === "relevance" && <RelevanceView />}
        {view === "isolation" && <IsolationView />}
        {view === "cost" && <CostView />}
        {view === "search" && <SearchView />}
      </main>
    </div>
  );
}

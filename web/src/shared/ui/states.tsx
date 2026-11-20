import type { ReactNode } from "react";
import type { Problem } from "../data";

/** A skeleton in the shape of what is coming: a heading line and a few rows. */
export function Loading({ rows = 5, label }: { rows?: number; label: string }) {
  return (
    <div role="status" aria-live="polite" aria-label={label} className="animate-pulse space-y-3">
      <div className="h-6 w-1/3 rounded-soft bg-line" />
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="h-4 rounded-soft bg-line" style={{ width: `${92 - i * 9}%` }} />
      ))}
    </div>
  );
}

export function ErrorState({ error, retry }: { error: Problem; retry: () => void }) {
  return (
    <div role="alert" className="max-w-prose rounded-card border border-bad bg-badWash p-5">
      <p className="font-semibold text-ink">{error.message}</p>
      <button type="button" onClick={retry} className="mt-3 rounded-soft bg-ink px-4 py-2 font-semibold text-sheet">
        Retry
      </button>
    </div>
  );
}

export function Empty({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="max-w-prose rounded-card border border-dashed border-muted p-5">
      <p className="font-semibold text-ink">{title}</p>
      <div className="mt-1 text-muted">{children}</div>
    </div>
  );
}

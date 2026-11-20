const FILL = ["bg-grade0 text-muted", "bg-grade1 text-ink", "bg-grade2 text-ink", "bg-grade3 text-sheet"] as const;
const WORD = ["not what was asked", "breaks a stated constraint", "acceptable", "everything asked for"] as const;

/** The hidden grade the world gave this product for this query: 0 to 3. */
export function Grade({ value }: { value: number }) {
  const g = Math.max(0, Math.min(3, value));
  return (
    <span
      className={`inline-flex h-chip w-chip shrink-0 items-center justify-center rounded-soft text-small font-bold ${FILL[g]}`}
      title={`Grade ${g}: ${WORD[g]}`}
      aria-label={`grade ${g}, ${WORD[g]}`}
    >
      {g}
    </span>
  );
}

export function GradeKey() {
  return (
    <p className="flex flex-wrap items-center gap-3 text-small text-muted">
      Hidden grade:
      {WORD.map((w, i) => (
        <span key={w} className="inline-flex items-center gap-1">
          <Grade value={i} /> {w}
        </span>
      ))}
    </p>
  );
}

/** Loading the generated reports and calling the live service, each with loading, error (with retry) and data. */
import { useCallback, useEffect, useState } from "react";
import type { Report, SearchAnswer } from "./types";

export class Problem extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

export type Resource<T> = { data: T | null; error: Problem | null; loading: boolean; retry: () => void };

async function getJson<T>(path: string): Promise<T> {
  let r: Response;
  try {
    r = await fetch(path, { headers: { accept: "application/json" } });
  } catch {
    throw new Problem(0, "The dashboard could not load its data. Check the connection and retry.");
  }
  if (r.status === 404) throw new Problem(404, "This report has not been generated yet.");
  if (!r.ok) throw new Problem(r.status, `Loading the report failed with HTTP ${r.status}.`);
  return (await r.json()) as T;
}

export function useResource<T>(path: string): Resource<T> {
  const [state, setState] = useState<{ data: T | null; error: Problem | null; loading: boolean }>({ data: null, error: null, loading: true });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let live = true;
    setState((s) => ({ ...s, loading: true, error: null }));
    getJson<T>(path)
      .then((data) => live && setState({ data, error: null, loading: false }))
      .catch((error: Problem) => live && setState({ data: null, error, loading: false }));
    return () => {
      live = false;
    };
  }, [path, attempt]);
  const retry = useCallback(() => setAttempt((x) => x + 1), []);
  return { ...state, retry };
}

export const useReport = (name: "dev" | "heldout" = "dev") => useResource<Report>(`/reports/${name}.json`);

export async function search(tenant: string, query: string, filters: Record<string, unknown> | null): Promise<SearchAnswer> {
  let r: Response;
  try {
    r = await fetch(`/v1/tenants/${encodeURIComponent(tenant)}/search`, {
      method: "POST",
      headers: { "content-type": "application/json", accept: "application/json" },
      body: JSON.stringify(filters ? { query, filters } : { query }),
    });
  } catch {
    throw new Problem(0, "The search service is not reachable. Start it with `java -jar service/target/scala-3.3.4/tenant-fair-search.jar`.");
  }
  const body = await r.json().catch(() => ({}));
  if (r.status === 429) throw new Problem(429, `This shop is over its rate. Retry in ${r.headers.get("Retry-After") ?? "a few"} s.`);
  if (!r.ok) throw new Problem(r.status, (body as { error?: string }).error ?? `The service answered ${r.status}.`);
  return body as SearchAnswer;
}

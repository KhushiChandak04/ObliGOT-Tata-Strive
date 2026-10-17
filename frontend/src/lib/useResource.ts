import { useCallback, useEffect, useRef, useState, type DependencyList } from "react";
import { ApiError } from "../services/functions.service";

export interface Resource<T> {
  data: T | null;
  error: ApiError | Error | null;
  loading: boolean;
  reload: () => void;
}

/** Load async data with loading/error state; responses from superseded requests are ignored. */
export function useResource<T>(load: () => Promise<T>, deps: DependencyList): Resource<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | Error | null>(null);
  const [loading, setLoading] = useState(true);
  const requestId = useRef(0);

  // `deps` controls when `load` is re-created, like useEffect's dependency list.
  const run = useCallback(load, deps);

  const reload = useCallback(() => {
    const current = ++requestId.current;
    setLoading(true);
    setError(null);
    run()
      .then((result) => { if (current === requestId.current) setData(result); })
      .catch((err: unknown) => {
        if (current !== requestId.current) return;
        // Drop earlier data so stale values are never shown next to an error.
        setData(null);
        setError(err instanceof Error ? err : new Error("Unexpected error"));
      })
      .finally(() => { if (current === requestId.current) setLoading(false); });
  }, [run]);

  useEffect(() => {
    reload();
    return () => { requestId.current++; };
  }, [reload]);

  return { data, error, loading, reload };
}

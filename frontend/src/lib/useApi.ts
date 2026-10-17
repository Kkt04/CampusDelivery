import { DependencyList, useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../api/client";

/** Load data on mount / when deps change, with loading and error state and a reload function. */
export function useApi<T>(loader: () => Promise<T>, deps: DependencyList) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const latest = useRef(0);

  const load = useCallback(async () => {
    const callId = ++latest.current;
    setLoading(true);
    setError(null);
    try {
      const result = await loader();
      if (callId === latest.current) setData(result);
    } catch (e) {
      if (callId === latest.current) setError(e instanceof ApiError ? e : new ApiError(0, "UNKNOWN", String(e)));
    } finally {
      if (callId === latest.current) setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    void load();
  }, [load]);

  return { data, error, loading, reload: load, setData };
}

/** Run a mutation with pending + error state. */
export function useAction<A extends unknown[], R>(action: (...args: A) => Promise<R>) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const run = useCallback(
    async (...args: A): Promise<R | undefined> => {
      setPending(true);
      setError(null);
      try {
        return await action(...args);
      } catch (e) {
        setError(e instanceof ApiError ? e : new ApiError(0, "UNKNOWN", String(e)));
        return undefined;
      } finally {
        setPending(false);
      }
    },
    [action],
  );
  return { run, pending, error, setError };
}

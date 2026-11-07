import { useCallback, useEffect, useState } from "react";
import { api } from "./client.js";

// Load once (and again when `deps` change or reload() is called): [data, error, reload, setData].
export function useResource(path, query, deps = []) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!path) return undefined;
    let alive = true;
    setError("");
    api(path, { query })
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e.message));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, tick, ...deps]);
  const reload = useCallback(() => setTick((n) => n + 1), []);
  return [data, error, reload, setData];
}

// The cohort list, shared by every page's cohort picker.
export function useCohorts() {
  const [data, error, reload] = useResource("cohorts/");
  return [data?.cohorts ?? null, error, reload];
}

// The cohort a page starts with: the running one, else the newest.
export function defaultCohort(cohorts) {
  if (!cohorts?.length) return null;
  return cohorts.find((c) => c.status === "running") || cohorts[0];
}

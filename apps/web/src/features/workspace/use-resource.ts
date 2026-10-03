"use client";

import { useEffect, useState } from "react";

type Snapshot<T> =
  { status: "loading" } | { status: "error" } | { status: "ready"; data: T };

export function useResource<T>(load: (signal: AbortSignal) => Promise<T>) {
  const [snapshot, setSnapshot] = useState<Snapshot<T>>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setSnapshot({ status: "ready", data });
      })
      .catch(() => {
        if (!controller.signal.aborted) setSnapshot({ status: "error" });
      });
    return () => controller.abort();
  }, [load, attempt]);
  function reload() {
    setSnapshot({ status: "loading" });
    setAttempt((value) => value + 1);
  }
  return { ...snapshot, reload };
}

"use client";

import { useCallback, useEffect, useState } from "react";
import { backend } from "./backend-api";
import type { Snapshot, Workspace } from "./backend-types";

export function useWorkspace(id: string) {
  const [data, setData] = useState<{
    workspace: Workspace | null;
    previous: Snapshot | null;
  }>({ workspace: null, previous: null });
  const [error, setError] = useState<string | null>(null);
  const accept = useCallback((workspace: Workspace) => {
    setData((old) => {
      if (
        old.workspace &&
        old.workspace.case_revision > workspace.case_revision
      )
        return old;
      const before = old.workspace?.aggregate.last_valid_result;
      const after = workspace.aggregate.current_result;
      const previous =
        before && after && before.snapshot_id !== after.snapshot_id
          ? before
          : old.previous;
      return { workspace, previous };
    });
    setError(null);
  }, []);
  const refresh = useCallback(async () => {
    const ws = await backend.workspace(id);
    accept(ws);
    return ws;
  }, [id, accept]);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      let delay = 2500;
      try {
        const ws = await backend.workspace(id, controller.signal);
        if (controller.signal.aborted) return;
        accept(ws);
        if (
          ws.stage === "extracting" ||
          ws.modules.some(
            (m) =>
              ["queued", "running"].includes(m.state) ||
              m.evidence.some((e) => e.parse_status === "pending"),
          )
        )
          delay = 800;
      } catch (e) {
        if (controller.signal.aborted) return;
        setError(
          e instanceof Error ? e.message : "Unable to refresh this case.",
        );
      }
      if (!controller.signal.aborted) timer = setTimeout(poll, delay);
    }
    void poll();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [id, accept]);
  return { ...data, error, refresh };
}

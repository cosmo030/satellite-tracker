import { useEffect, useState } from 'react';

import type { ApiClient } from '../api/client';
import type { FromWorker, ToWorker } from '../orbit/workerProtocol';

export interface GroupSatellites {
  noradIds: number[];
  positions: Float64Array | null;
  isLoading: boolean;
  error: string | null;
}

interface Loaded {
  group: string;
  noradIds: number[];
  positions: Float64Array | null;
  error: string | null;
}

const NO_IDS: number[] = [];

/**
 * Loads a group's element sets and keeps live positions for them, computed by the
 * propagation worker at 2 Hz.
 */
export function useGroupSatellites(api: ApiClient, group: string | null): GroupSatellites {
  const [loaded, setLoaded] = useState<Loaded | null>(null);

  useEffect(() => {
    if (!group) return;
    const worker = new Worker(new URL('../orbit/propagation.worker.ts', import.meta.url), {
      type: 'module',
    });
    const controller = new AbortController();
    worker.onmessage = (event: MessageEvent<FromWorker>) => {
      const message = event.data;
      if (message.type === 'loaded') {
        setLoaded({ group, noradIds: message.noradIds, positions: null, error: null });
      } else {
        setLoaded((previous) =>
          previous?.group === group ? { ...previous, positions: message.positions } : previous,
        );
      }
    };
    api
      .groupElements(group, controller.signal)
      .then((elements) => {
        const message: ToWorker = { type: 'load', elements };
        worker.postMessage(message);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setLoaded({
          group,
          noradIds: NO_IDS,
          positions: null,
          error: `Could not load group "${group}": ${String(error)}`,
        });
      });
    return () => {
      controller.abort();
      worker.terminate();
    };
  }, [api, group]);

  // Data from a previously selected group is never shown for the current one.
  const current = loaded && loaded.group === group ? loaded : null;
  return {
    noradIds: current?.noradIds ?? NO_IDS,
    positions: current?.positions ?? null,
    isLoading: group !== null && current === null,
    error: current?.error ?? null,
  };
}

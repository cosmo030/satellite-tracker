import { useEffect, useSyncExternalStore } from 'react';

import type { ApiClient, SatelliteAbout, SatelliteDetail } from '../api/client';

/** Descriptions fetched this session, by NORAD ID; null means "none" (404 or failed). */
const cache = new Map<number, SatelliteAbout | null>();
const listeners = new Set<() => void>();

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function store(noradId: number, about: SatelliteAbout | null): void {
  cache.set(noradId, about);
  listeners.forEach((listener) => {
    listener();
  });
}

/**
 * The description of the object in ``detail``, fetched only when the detail says ``has_about``.
 * Keyed by the detail shown, so text never pairs with another object's facts. Results are
 * cached for the session. Errors and 404s give null: the tile then looks exactly as it does
 * without a description.
 */
export function useSatelliteAbout(
  api: ApiClient,
  detail: SatelliteDetail | null,
): SatelliteAbout | null {
  const noradId = detail?.satellite.norad_id ?? null;
  const hasAbout = detail?.has_about ?? false;
  const about = useSyncExternalStore(subscribe, () =>
    noradId === null ? null : (cache.get(noradId) ?? null),
  );

  useEffect(() => {
    if (noradId === null || !hasAbout || cache.has(noradId)) return;
    const controller = new AbortController();
    api
      .satelliteAbout(noradId, controller.signal)
      .then((result) => {
        store(noradId, result);
      })
      .catch(() => {
        if (!controller.signal.aborted) store(noradId, null);
      });
    return () => {
      controller.abort();
    };
  }, [api, noradId, hasAbout]);

  return hasAbout ? about : null;
}

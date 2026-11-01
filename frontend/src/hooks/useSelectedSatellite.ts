import { useEffect, useMemo, useState } from 'react';

import type { ApiClient, SatelliteDetail } from '../api/client';
import {
  createSatrec,
  orbitTrack,
  stateAt,
  type GeoPosition,
  type SatelliteState,
} from '../orbit/propagation';

/** The orbit path is recomputed this often so it keeps starting at the satellite. */
const TRACK_REFRESH_MS = 60_000;

export interface SelectedSatellite {
  detail: SatelliteDetail | null;
  state: SatelliteState | null;
  track: GeoPosition[];
  error: string | null;
}

interface Loaded {
  noradId: number;
  detail: SatelliteDetail | null;
  error: string | null;
}

/** Loads the selected satellite's details and computes its live state and orbit track. */
export function useSelectedSatellite(
  api: ApiClient,
  noradId: number | null,
  now: Date,
): SelectedSatellite {
  const [loaded, setLoaded] = useState<Loaded | null>(null);

  useEffect(() => {
    if (noradId === null) return;
    const controller = new AbortController();
    api
      .satelliteDetail(noradId, controller.signal)
      .then((detail) => {
        setLoaded({ noradId, detail, error: null });
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setLoaded({ noradId, detail: null, error: String(reason) });
      });
    return () => {
      controller.abort();
    };
  }, [api, noradId]);

  const current = currentSelection(loaded, noradId);
  const elements = current.detail?.latest_elements ?? null;
  const satrec = useMemo(() => (elements ? createSatrec(elements) : null), [elements]);
  const trackWindow = Math.floor(now.getTime() / TRACK_REFRESH_MS);

  const track = useMemo(() => {
    if (!satrec || !elements) return [];
    return orbitTrack(satrec, new Date(trackWindow * TRACK_REFRESH_MS), elements.period_minutes);
  }, [satrec, elements, trackWindow]);

  return {
    detail: current.detail,
    state: satrec ? stateAt(satrec, now) : null,
    track,
    error: current.error,
  };
}

/** The loaded data if it belongs to the current selection; a previous response is ignored. */
function currentSelection(
  loaded: Loaded | null,
  noradId: number | null,
): Pick<Loaded, 'detail' | 'error'> {
  if (loaded && loaded.noradId === noradId) return loaded;
  return { detail: null, error: null };
}

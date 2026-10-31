import { useEffect, useState } from 'react';

import type { ApiClient, SatellitePage, SatelliteSearch } from '../api/client';

const DEBOUNCE_MS = 300;

export interface SearchState {
  page: SatellitePage | null;
  error: string | null;
}

/** Runs a satellite search shortly after the criteria stop changing. */
export function useSatelliteSearch(api: ApiClient, search: SatelliteSearch): SearchState {
  const [state, setState] = useState<SearchState>({ page: null, error: null });
  const key = JSON.stringify(search);

  useEffect(() => {
    const criteria = JSON.parse(key) as SatelliteSearch;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      api
        .searchSatellites(criteria, controller.signal)
        .then((page) => {
          setState({ page, error: null });
        })
        .catch((error: unknown) => {
          if (!controller.signal.aborted) setState({ page: null, error: String(error) });
        });
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [api, key]);

  return state;
}

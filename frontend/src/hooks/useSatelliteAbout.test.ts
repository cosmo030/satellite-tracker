// @vitest-environment jsdom
import { cleanup, renderHook, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ApiClient, type SatelliteDetail } from '../api/client';
import { about, detail } from '../components/aboutFixtures';
import { useSatelliteAbout } from './useSatelliteAbout';

afterEach(cleanup);

function apiAnswering(status: number, body: unknown = {}) {
  const fetchFn = vi.fn(() => Promise.resolve(new Response(JSON.stringify(body), { status })));
  return { api: new ApiClient(fetchFn), fetchFn };
}

function detailOf(noradId: number, hasAbout: boolean): SatelliteDetail {
  return {
    ...detail,
    satellite: { ...detail.satellite, norad_id: noradId },
    has_about: hasAbout,
  };
}

describe('useSatelliteAbout', () => {
  it('does not ask the API when the detail has no description', () => {
    const { api, fetchFn } = apiAnswering(200, about());

    const { result } = renderHook(() => useSatelliteAbout(api, detailOf(70001, false)));

    expect(result.current).toBeNull();
    expect(fetchFn).not.toHaveBeenCalled();
  });

  it('fetches once and caches the description for the session', async () => {
    const { api, fetchFn } = apiAnswering(200, about({ norad_id: 70002 }));
    const shown = detailOf(70002, true);

    const first = renderHook(() => useSatelliteAbout(api, shown));
    await waitFor(() => {
      expect(first.result.current?.norad_id).toBe(70002);
    });
    const second = renderHook(() => useSatelliteAbout(api, shown));

    expect(second.result.current?.norad_id).toBe(70002);
    expect(fetchFn).toHaveBeenCalledTimes(1);
    expect(fetchFn).toHaveBeenCalledWith('/api/v1/satellites/70002/about', expect.anything());
  });

  it('gives null when the API has nothing', async () => {
    const { api, fetchFn } = apiAnswering(404);

    const { result } = renderHook(() => useSatelliteAbout(api, detailOf(70003, true)));

    await waitFor(() => {
      expect(fetchFn).toHaveBeenCalledTimes(1);
    });
    expect(result.current).toBeNull();
  });
});

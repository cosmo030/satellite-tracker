import { describe, expect, it, vi } from 'vitest';

import { ApiClient, ApiError, searchQueryString, withSearchChanges } from './client';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('searchQueryString', () => {
  it('maps search fields to API parameters and drops empty ones', () => {
    const query = searchQueryString({
      q: '  iss ',
      orbitClass: 'LEO',
      country: ' us ',
      launchYear: 1998,
      limit: 25,
    });
    expect(query).toBe('q=iss&orbit_class=LEO&country=US&launch_year=1998&limit=25');
  });

  it('omits a blank query', () => {
    expect(searchQueryString({ q: '   ', group: 'stations' })).toBe('group=stations');
  });

  it('encodes special characters', () => {
    expect(searchQueryString({ q: 'R/B & DEB' })).toBe('q=R%2FB+%26+DEB');
  });
});

describe('withSearchChanges', () => {
  it('sets, replaces and removes criteria without mutating the input', () => {
    const original = { q: 'iss', orbitClass: 'LEO' as const, limit: 25 };

    const next = withSearchChanges(original, { q: '', orbitClass: 'GEO', launchYear: undefined });

    expect(next).toEqual({ orbitClass: 'GEO', limit: 25 });
    expect(original).toEqual({ q: 'iss', orbitClass: 'LEO', limit: 25 });
  });
});

describe('ApiClient', () => {
  it('requests group elements from the versioned API path', async () => {
    const fetchFn = vi.fn().mockResolvedValue(jsonResponse([]));

    await new ApiClient(fetchFn).groupElements('gps-ops');

    expect(fetchFn).toHaveBeenCalledWith(
      '/api/v1/elements?group=gps-ops',
      expect.objectContaining({ headers: { Accept: 'application/json' } }),
    );
  });

  it('returns parsed JSON', async () => {
    const groups = [{ slug: 'stations', name: 'Space stations', satellite_count: 3 }];
    const client = new ApiClient(vi.fn().mockResolvedValue(jsonResponse(groups)));

    await expect(client.listGroups()).resolves.toEqual(groups);
  });

  it('throws ApiError with status and path on a non-OK response', async () => {
    const client = new ApiClient(vi.fn().mockResolvedValue(jsonResponse({ detail: 'x' }, 404)));

    const error: unknown = await client.satelliteDetail(424242).catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 404, path: '/satellites/424242' });
  });

  it('passes the abort signal through', async () => {
    const fetchFn = vi.fn().mockResolvedValue(jsonResponse({ items: [], total: 0 }));
    const controller = new AbortController();

    await new ApiClient(fetchFn).searchSatellites({ q: 'x' }, controller.signal);

    expect(fetchFn).toHaveBeenCalledWith(
      '/api/v1/satellites?q=x',
      expect.objectContaining({ signal: controller.signal }),
    );
  });
});

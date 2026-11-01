/**
 * Typed client for the Satellite Tracker REST API (see docs/openapi.json).
 * The API is served from the same origin under /api/v1.
 */

export const API_BASE_PATH = '/api/v1';

export type OrbitClass = 'LEO' | 'MEO' | 'GEO' | 'HEO' | 'OTHER';
export const ORBIT_CLASSES: readonly OrbitClass[] = ['LEO', 'MEO', 'GEO', 'HEO', 'OTHER'];

export interface Group {
  slug: string;
  name: string;
  satellite_count: number;
}

export interface Satellite {
  norad_id: number;
  name: string;
  intl_designator: string | null;
  object_type: string | null;
  country: string | null;
  launch_date: string | null;
  orbit_class: OrbitClass | null;
}

export interface SatellitePage {
  items: Satellite[];
  total: number;
  limit: number;
  offset: number;
}

export interface ElementSet {
  norad_id: number;
  object_name: string;
  object_id: string | null;
  epoch: string;
  mean_motion: number;
  eccentricity: number;
  inclination_deg: number;
  raan_deg: number;
  arg_of_pericenter_deg: number;
  mean_anomaly_deg: number;
  bstar: number;
  mean_motion_dot: number;
  mean_motion_ddot: number;
  element_set_no: number | null;
  rev_at_epoch: number | null;
  classification_type: string;
  ephemeris_type: number;
  period_minutes: number;
  orbit_class: OrbitClass;
}

export interface SatelliteDetail {
  satellite: Satellite;
  latest_elements: ElementSet | null;
  /** A description is available from ``satelliteAbout``. */
  has_about: boolean;
  has_image: boolean;
}

/** Purpose categories, in display priority order. */
export type AboutCategory =
  | 'space_station'
  | 'crewed'
  | 'telescope'
  | 'earth_observation'
  | 'weather'
  | 'navigation'
  | 'communications'
  | 'science'
  | 'technology'
  | 'amateur'
  | 'military'
  | 'cubesat';

/** A Wikimedia Commons image served by our API; always shown with its credit. */
export interface AboutImage {
  url_480: string;
  url_960: string;
  width_480: number;
  height_480: number;
  artist: string;
  license_short: string;
  license_url: string | null;
  source_url: string;
  alt_text: string;
}

/** What Wikimedia says about an object (descriptions are CC BY-SA 4.0 or CC0). */
export interface SatelliteAbout {
  norad_id: number;
  /** "constellation": the text describes the constellation the object belongs to. */
  scope: 'object' | 'constellation';
  title: string | null;
  summary: string | null;
  summary_source: 'wikipedia' | 'wikidata' | null;
  summary_url: string | null;
  summary_license: string | null;
  categories: AboutCategory[];
  operators: string[];
  manufacturers: string[];
  image: AboutImage | null;
  fetched_at: string;
}

export interface SatelliteSearch {
  q?: string;
  group?: string;
  orbitClass?: OrbitClass;
  country?: string;
  launchYear?: number;
  limit?: number;
  offset?: number;
}

/** Changes to apply to a search; ``undefined`` or an empty string removes the criterion. */
export type SearchChanges = {
  [K in keyof SatelliteSearch]?: SatelliteSearch[K] | '' | undefined;
};

export function withSearchChanges(
  search: SatelliteSearch,
  changes: SearchChanges,
): SatelliteSearch {
  const merged: Record<string, unknown> = { ...search, ...changes };
  const kept = Object.entries(merged).filter(([, value]) => value !== undefined && value !== '');
  return Object.fromEntries(kept);
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly path: string,
  ) {
    super(`API request to ${path} failed with HTTP ${status}`);
    this.name = 'ApiError';
  }
}

type Fetch = (input: string, init?: RequestInit) => Promise<Response>;

export function searchQueryString(search: SatelliteSearch): string {
  const params = new URLSearchParams();
  const entries: [string, string | number | undefined][] = [
    ['q', search.q?.trim() || undefined],
    ['group', search.group],
    ['orbit_class', search.orbitClass],
    ['country', search.country?.trim().toUpperCase() || undefined],
    ['launch_year', search.launchYear],
    ['limit', search.limit],
    ['offset', search.offset],
  ];
  for (const [key, value] of entries) {
    if (value !== undefined) params.set(key, String(value));
  }
  return params.toString();
}

export class ApiClient {
  constructor(private readonly fetchFn: Fetch = (input, init) => fetch(input, init)) {}

  listGroups(signal?: AbortSignal): Promise<Group[]> {
    return this.get<Group[]>('/groups', signal);
  }

  groupElements(group: string, signal?: AbortSignal): Promise<ElementSet[]> {
    return this.get<ElementSet[]>(`/elements?group=${encodeURIComponent(group)}`, signal);
  }

  searchSatellites(search: SatelliteSearch, signal?: AbortSignal): Promise<SatellitePage> {
    return this.get<SatellitePage>(`/satellites?${searchQueryString(search)}`, signal);
  }

  satelliteDetail(noradId: number, signal?: AbortSignal): Promise<SatelliteDetail> {
    return this.get<SatelliteDetail>(`/satellites/${noradId}`, signal);
  }

  /** Description and image credit; rejects with ``ApiError`` 404 when there is none. */
  satelliteAbout(noradId: number, signal?: AbortSignal): Promise<SatelliteAbout> {
    return this.get<SatelliteAbout>(`/satellites/${noradId}/about`, signal);
  }

  private async get<T>(path: string, signal?: AbortSignal): Promise<T> {
    const init: RequestInit = { headers: { Accept: 'application/json' } };
    if (signal) init.signal = signal;
    const response = await this.fetchFn(`${API_BASE_PATH}${path}`, init);
    if (!response.ok) throw new ApiError(response.status, path);
    return (await response.json()) as T;
  }
}

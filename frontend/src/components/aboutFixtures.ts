import type { AboutImage, SatelliteAbout, SatelliteDetail } from '../api/client';

/** Synthetic test data only: no real Wikipedia text or Commons files. */

export const detail: SatelliteDetail = {
  satellite: {
    norad_id: 90001,
    name: 'TESTSAT 1',
    intl_designator: '2020-001A',
    object_type: 'PAYLOAD',
    country: 'US',
    launch_date: '2020-01-15',
    orbit_class: 'LEO',
  },
  latest_elements: {
    norad_id: 90001,
    object_name: 'TESTSAT 1',
    object_id: '2020-001A',
    epoch: '2026-11-01T10:00:00Z',
    mean_motion: 15.5,
    eccentricity: 0.0005,
    inclination_deg: 51.6,
    raan_deg: 120,
    arg_of_pericenter_deg: 90,
    mean_anomaly_deg: 10,
    bstar: 0.0001,
    mean_motion_dot: 0,
    mean_motion_ddot: 0,
    element_set_no: 999,
    rev_at_epoch: 1000,
    classification_type: 'U',
    ephemeris_type: 0,
    period_minutes: 92.9,
    orbit_class: 'LEO',
  },
  has_about: false,
  has_image: false,
};

export const image: AboutImage = {
  url_480: '/api/v1/satellites/90001/image?w=480',
  url_960: '/api/v1/satellites/90001/image?w=960',
  width_480: 480,
  height_480: 320,
  artist: 'Test Photographer',
  license_short: 'CC BY-SA 4.0',
  license_url: 'https://creativecommons.org/licenses/by-sa/4.0',
  source_url: 'https://commons.wikimedia.org/wiki/File:Synthetic_station.jpg',
  alt_text: 'A made-up satellite',
};

export function about(changes: Partial<SatelliteAbout> = {}): SatelliteAbout {
  return {
    norad_id: 90001,
    scope: 'object',
    title: 'Testsat',
    summary: 'Testsat is a made-up satellite. It exists only in tests.',
    summary_source: 'wikipedia',
    summary_url: 'https://en.wikipedia.org/wiki/Testsat',
    summary_license: 'CC BY-SA 4.0',
    categories: ['science', 'cubesat'],
    operators: ['Agency One', 'Agency Two'],
    manufacturers: ['Maker Inc'],
    image,
    fetched_at: '2026-11-01T00:00:00Z',
    ...changes,
  };
}

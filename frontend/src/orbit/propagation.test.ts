import { describe, expect, it } from 'vitest';

import type { ElementSet } from '../api/client';
import {
  POSITION_STRIDE,
  createSatrec,
  orbitTrack,
  propagateAll,
  stateAt,
  toOmm,
} from './propagation';

// Sample element sets (made-up values close to real orbits), matching the backend fixtures.
function elementSet(overrides: Partial<ElementSet> = {}): ElementSet {
  return {
    norad_id: 25544,
    object_name: 'ISS (ZARYA)',
    object_id: '1998-067A',
    epoch: '2026-10-30T12:00:00Z',
    mean_motion: 15.50103472,
    eccentricity: 0.0006703,
    inclination_deg: 51.6416,
    raan_deg: 247.4627,
    arg_of_pericenter_deg: 130.536,
    mean_anomaly_deg: 325.0288,
    bstar: 0.00034,
    mean_motion_dot: 0.0002,
    mean_motion_ddot: 0,
    element_set_no: 999,
    rev_at_epoch: 48000,
    classification_type: 'U',
    ephemeris_type: 0,
    period_minutes: 92.897,
    orbit_class: 'LEO',
    ...overrides,
  };
}

const GEO = elementSet({
  norad_id: 45001,
  object_name: 'TESTSAT GEO-2',
  mean_motion: 1.00271,
  eccentricity: 0.0002,
  inclination_deg: 0.05,
  raan_deg: 80,
  arg_of_pericenter_deg: 10,
  mean_anomaly_deg: 300,
  bstar: 0,
  mean_motion_dot: 0,
  period_minutes: 1436.1,
  orbit_class: 'GEO',
});

// A very low orbit with extreme drag: already decayed, so SGP4 refuses to propagate it.
const IMPOSSIBLE = elementSet({ norad_id: 1, mean_motion: 16.9, eccentricity: 0.0001, bstar: 0.5 });

const TEN_MINUTES_AFTER_EPOCH = new Date('2026-10-30T12:10:00Z');

describe('toOmm', () => {
  it('sends the epoch as UTC without a zone designator, like CelesTrak', () => {
    expect(toOmm(elementSet()).EPOCH).toBe('2026-10-30T12:00:00.000');
  });

  it('maps degrees and identifiers to OMM keys', () => {
    const omm = toOmm(elementSet());
    expect(omm.NORAD_CAT_ID).toBe(25544);
    expect(omm.RA_OF_ASC_NODE).toBe(247.4627);
    expect(omm.OBJECT_ID).toBe('1998-067A');
  });

  it('fills defaults for optional fields the API may omit', () => {
    const omm = toOmm(elementSet({ object_id: null, element_set_no: null, rev_at_epoch: null }));
    expect(omm.OBJECT_ID).toBe('');
    expect(omm.ELEMENT_SET_NO).toBe(999);
    expect(omm.REV_AT_EPOCH).toBe(0);
  });
});

describe('stateAt', () => {
  it('puts a LEO station at a plausible altitude, latitude and speed', () => {
    const state = stateAt(createSatrec(elementSet()), TEN_MINUTES_AFTER_EPOCH);

    expect(state).not.toBeNull();
    expect(state?.heightKm).toBeGreaterThan(400);
    expect(state?.heightKm).toBeLessThan(440);
    expect(Math.abs(state?.latitudeDeg ?? 99)).toBeLessThanOrEqual(51.7);
    expect(state?.longitudeDeg).toBeGreaterThanOrEqual(-180);
    expect(state?.longitudeDeg).toBeLessThanOrEqual(180);
    expect(state?.speedKmPerS).toBeCloseTo(7.66, 1);
  });

  it('keeps a geostationary satellite near the same longitude over an hour', () => {
    const satrec = createSatrec(GEO);
    const first = stateAt(satrec, TEN_MINUTES_AFTER_EPOCH);
    const later = stateAt(satrec, new Date(TEN_MINUTES_AFTER_EPOCH.getTime() + 3_600_000));

    expect(first?.heightKm).toBeCloseTo(35786, -2);
    expect(Math.abs((later?.longitudeDeg ?? 0) - (first?.longitudeDeg ?? 0))).toBeLessThan(0.5);
  });

  it('returns null when SGP4 cannot propagate the orbit', () => {
    expect(stateAt(createSatrec(IMPOSSIBLE), TEN_MINUTES_AFTER_EPOCH)).toBeNull();
  });
});

describe('propagateAll', () => {
  it('packs longitude, latitude and height per satellite in input order', () => {
    const satrecs = [createSatrec(elementSet()), createSatrec(GEO)];

    const buffer = propagateAll(satrecs, TEN_MINUTES_AFTER_EPOCH);

    expect(buffer).toHaveLength(2 * POSITION_STRIDE);
    const single = stateAt(satrecs[1]!, TEN_MINUTES_AFTER_EPOCH); // eslint-disable-line @typescript-eslint/no-non-null-assertion -- index 1 exists: two satrecs were created above
    expect(buffer[3]).toBeCloseTo(single?.longitudeDeg ?? 0, 6);
    expect(buffer[4]).toBeCloseTo(single?.latitudeDeg ?? 0, 6);
    expect(buffer[5]).toBeCloseTo(single?.heightKm ?? 0, 3);
  });

  it('fills NaN for satellites that cannot be propagated, keeping the others aligned', () => {
    const buffer = propagateAll(
      [createSatrec(IMPOSSIBLE), createSatrec(elementSet())],
      TEN_MINUTES_AFTER_EPOCH,
    );

    expect(Array.from(buffer.slice(0, 3)).every(Number.isNaN)).toBe(true);
    expect(buffer[5]).toBeGreaterThan(400);
  });

  it('returns an empty buffer for no satellites', () => {
    expect(propagateAll([], TEN_MINUTES_AFTER_EPOCH)).toHaveLength(0);
  });
});

describe('orbitTrack', () => {
  it('samples one period and returns to the starting latitude', () => {
    const track = orbitTrack(createSatrec(elementSet()), TEN_MINUTES_AFTER_EPOCH, 92.897, 90);

    expect(track).toHaveLength(91);
    const first = track[0];
    const last = track.at(-1);
    expect(Math.abs((last?.latitudeDeg ?? 0) - (first?.latitudeDeg ?? 0))).toBeLessThan(1);
  });

  it('skips points SGP4 cannot compute', () => {
    expect(orbitTrack(createSatrec(IMPOSSIBLE), TEN_MINUTES_AFTER_EPOCH, 90, 10)).toEqual([]);
  });
});

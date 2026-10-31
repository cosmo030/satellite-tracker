import { describe, expect, it } from 'vitest';

import {
  epochAgeMs,
  formatAge,
  formatDegrees,
  formatKm,
  formatPeriod,
  formatSpeed,
  isEpochStale,
} from './format';

const NOW = new Date('2026-10-31T12:00:00Z');
const HOUR_MS = 3_600_000;

describe('epoch staleness', () => {
  it('measures the age of an epoch', () => {
    expect(epochAgeMs('2026-10-31T10:00:00Z', NOW)).toBe(2 * HOUR_MS);
  });

  it('is not stale at exactly three days', () => {
    expect(isEpochStale('2026-10-28T12:00:00Z', NOW)).toBe(false);
  });

  it('is stale after three days', () => {
    expect(isEpochStale('2026-10-28T11:59:59Z', NOW)).toBe(true);
  });
});

describe('formatAge', () => {
  it.each([
    [5 * 60_000, '5 min ago'],
    [3 * HOUR_MS, '3 h ago'],
    [47 * HOUR_MS, '47 h ago'],
    [72 * HOUR_MS, '3 days ago'],
    [-30 * 60_000, '30 min from now'],
  ])('formats %d ms as %s', (ageMs, expected) => {
    expect(formatAge(ageMs)).toBe(expected);
  });
});

describe('number formatting', () => {
  it('rounds kilometres and adds separators', () => {
    expect(formatKm(35786.4)).toBe('35,786 km');
  });

  it('formats speed, degrees and periods', () => {
    expect(formatSpeed(7.6612)).toBe('7.66 km/s');
    expect(formatDegrees(-51.64159)).toBe('-51.64°');
    expect(formatPeriod(92.897)).toBe('92.9 min');
    expect(formatPeriod(1436.4)).toBe('23.94 h');
  });
});

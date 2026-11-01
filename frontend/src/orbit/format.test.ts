import { describe, expect, it } from 'vitest';

import {
  epochAgeMs,
  epochFreshness,
  formatCalendarDate,
  formatCount,
  formatDegrees,
  formatElementAge,
  formatFixed,
  formatPeriod,
  formatUtcClock,
  formatUtcTimestamp,
  isEpochStale,
} from './format';

const NOW = new Date('2026-10-31T12:00:00Z');
const MINUTE_MS = 60_000;
const HOUR_MS = 3_600_000;
const DAY_MS = 86_400_000;

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

describe('epochFreshness', () => {
  it.each([
    [7 * HOUR_MS, 'fresh'],
    [DAY_MS - 1, 'fresh'],
    [DAY_MS, 'aging'],
    [3 * DAY_MS, 'aging'],
    [3 * DAY_MS + 1, 'stale'],
    [-HOUR_MS, 'fresh'],
  ] as const)('classifies an age of %d ms as %s', (ageMs, expected) => {
    expect(epochFreshness(ageMs)).toBe(expected);
  });
});

describe('formatElementAge', () => {
  it.each([
    [5 * MINUTE_MS, '5 min old'],
    [7 * HOUR_MS, '7 h old'],
    [47 * HOUR_MS, '47 h old'],
    [4 * DAY_MS, '4 d old'],
    [-30 * MINUTE_MS, 'in 30 min'],
  ])('formats %d ms as %s', (ageMs, expected) => {
    expect(formatElementAge(ageMs)).toBe(expected);
  });
});

describe('number formatting', () => {
  it('uses a true minus sign for negative values', () => {
    expect(formatFixed(-15.194, 2)).toBe('−15.19');
    expect(formatDegrees(-51.64159)).toBe('−51.64°');
  });

  it('does not show a minus sign for values that round to zero', () => {
    expect(formatFixed(-0.004, 2)).toBe('0.00');
  });

  it('formats fixed decimals, degrees, periods and counts', () => {
    expect(formatFixed(594.66, 1)).toBe('594.7');
    expect(formatFixed(7.5634, 3)).toBe('7.563');
    expect(formatDegrees(97.5)).toBe('97.50°');
    expect(formatPeriod(92.897)).toBe('92.9 min');
    expect(formatPeriod(1436.4)).toBe('23.94 h');
    expect(formatCount(11156)).toBe('11,156');
  });
});

describe('date and time formatting', () => {
  it('formats catalog dates as day, short month and year', () => {
    expect(formatCalendarDate('2017-07-14')).toBe('14 Jul 2017');
    expect(formatCalendarDate('1998-11-20')).toBe('20 Nov 1998');
  });

  it('rejects unreadable catalog dates', () => {
    expect(formatCalendarDate('unknown')).toBeNull();
    expect(formatCalendarDate('2017-13-01')).toBeNull();
  });

  it('formats UTC clock times and timestamps in 24-hour time', () => {
    const date = new Date('2026-11-01T07:12:04.900Z');
    expect(formatUtcClock(date)).toBe('07:12:04');
    expect(formatUtcTimestamp(date)).toBe('1 Nov 2026, 07:12:04 UTC');
  });
});

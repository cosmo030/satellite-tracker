import { describe, expect, it } from 'vitest';

import { hourTicks, utcDayFraction } from './timeline';

describe('utcDayFraction', () => {
  it('is 0 at UTC midnight and 0.5 at UTC noon', () => {
    expect(utcDayFraction(new Date('2026-11-01T00:00:00Z'))).toBe(0);
    expect(utcDayFraction(new Date('2026-11-01T12:00:00Z'))).toBe(0.5);
  });

  it('uses UTC, not the local time zone', () => {
    expect(utcDayFraction(new Date('2026-11-01T18:00:00+02:00'))).toBe(16 / 24);
  });
});

describe('hourTicks', () => {
  it('has a tick per hour from 0 to 24, with major ticks every six hours', () => {
    const ticks = hourTicks();
    expect(ticks).toHaveLength(25);
    expect(ticks[0]).toEqual({ hour: 0, position: 0, major: true });
    expect(ticks[24]).toEqual({ hour: 24, position: 1, major: true });
    expect(ticks.filter((tick) => tick.major).map((tick) => tick.hour)).toEqual([0, 6, 12, 18, 24]);
  });
});

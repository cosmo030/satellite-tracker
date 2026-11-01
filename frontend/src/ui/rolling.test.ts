import { describe, expect, it } from 'vitest';

import {
  digitsByPlace,
  initialRollState,
  nextRollState,
  normalizeIndex,
  rollDirection,
  rollTarget,
  staggerDelay,
  STRIP_DIGITS,
  tokenize,
} from './rolling';

describe('tokenize', () => {
  it('numbers digits by place from the right and keeps separators static', () => {
    expect(tokenize('7,412')).toEqual([
      { kind: 'digit', digit: 7, place: 3 },
      { kind: 'static', char: ',', key: '3:,' },
      { kind: 'digit', digit: 4, place: 2 },
      { kind: 'digit', digit: 1, place: 1 },
      { kind: 'digit', digit: 2, place: 0 },
    ]);
  });

  it('handles separators that are not commas', () => {
    expect(tokenize('11.156').filter((token) => token.kind === 'static')).toEqual([
      { kind: 'static', char: '.', key: '3:.' },
    ]);
  });
});

describe('digitsByPlace', () => {
  it('puts the ones digit first and ignores separators', () => {
    expect(digitsByPlace('1,203')).toEqual([3, 0, 2, 1]);
  });
});

describe('rollDirection', () => {
  it('rolls up for increases, down for decreases, and not at all otherwise', () => {
    expect(rollDirection(19, 20)).toBe('up');
    expect(rollDirection(20, 19)).toBe('down');
    expect(rollDirection(5, 5)).toBeNull();
  });
});

describe('staggerDelay', () => {
  it('starts the ones first and caps the delay at 150 ms', () => {
    expect([0, 1, 2, 3, 4].map(staggerDelay)).toEqual([0, 50, 100, 150, 150]);
  });
});

describe('nextRollState', () => {
  it('moves only the digits that changed, ones first', () => {
    const state = nextRollState(initialRollState(1203, '1,203'), 1213, '1,213');
    expect(state.direction).toBe('up');
    expect(state.delays).toEqual({ 1: 0 });
    expect(state.entering).toEqual([]);
    expect(state.exits).toEqual([]);
  });

  it('staggers several changed digits from the right', () => {
    const state = nextRollState(initialRollState(199, '199'), 200, '200');
    expect(state.delays).toEqual({ 0: 0, 1: 50, 2: 100 });
  });

  it('rolls in a new leading digit (99 → 100)', () => {
    const state = nextRollState(initialRollState(99, '99'), 100, '100');
    expect(state.direction).toBe('up');
    expect(state.entering).toEqual([2]);
    expect(state.delays).toEqual({ 0: 0, 1: 50, 2: 100 });
  });

  it('fades out a removed leading digit (100 → 99)', () => {
    const state = nextRollState(initialRollState(100, '100'), 99, '99');
    expect(state.direction).toBe('down');
    expect(state.exits).toEqual([{ id: '100@2', place: 2, digit: 1 }]);
    expect(state.delays).toEqual({ 0: 0, 1: 50 });
  });

  it('keeps fading digits that are still beyond the new value and drops those that return', () => {
    const fading = nextRollState(initialRollState(1000, '1,000'), 999, '999');
    expect(fading.exits.map((exit) => exit.place)).toEqual([3]);
    expect(nextRollState(fading, 998, '998').exits.map((exit) => exit.place)).toEqual([3]);
    expect(nextRollState(fading, 1001, '1,001').exits).toEqual([]);
  });

  it('crosses a separator boundary by rolling digits only', () => {
    const state = nextRollState(initialRollState(999, '999'), 1000, '1,000');
    expect(state.entering).toEqual([3]);
    expect(Object.keys(state.delays).map(Number)).toEqual([0, 1, 2, 3]);
  });
});

describe('rollTarget', () => {
  it('rolls up to the next copy when the digit wraps past 9 → 0', () => {
    expect(rollTarget(19, 0, 'up')).toBe(20);
    expect(rollTarget(13, 7, 'up')).toBe(17);
  });

  it('rolls down to the previous copy when the digit wraps past 0 → 9', () => {
    expect(rollTarget(10, 9, 'down')).toBe(9);
    expect(rollTarget(17, 3, 'down')).toBe(13);
  });

  it('retargets from a mid-roll position in the new direction', () => {
    // Halfway from 4 to 5 (index 14.5), the value drops back to 4: roll down to 4.
    expect(rollTarget(14.5, 4, 'down')).toBe(14);
    // Halfway from 9 to 0 in the next copy (index 19.5), it rises to 1: keep rolling up.
    expect(rollTarget(19.5, 1, 'up')).toBe(21);
  });

  it('always stays inside the strip, whatever the starting copy', () => {
    for (let from = 0; from < STRIP_DIGITS; from += 0.5) {
      for (let digit = 0; digit <= 9; digit++) {
        for (const direction of ['up', 'down'] as const) {
          const target = rollTarget(from, digit, direction);
          expect(target).toBeGreaterThanOrEqual(0);
          expect(target).toBeLessThan(STRIP_DIGITS);
          expect(target % 10).toBe(digit);
        }
      }
    }
  });
});

describe('normalizeIndex', () => {
  it('maps any copy onto the middle copy without changing the digit shown', () => {
    expect(normalizeIndex(3)).toBe(13);
    expect(normalizeIndex(27.5)).toBe(17.5);
    expect(normalizeIndex(15)).toBe(15);
  });
});

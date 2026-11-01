import { describe, expect, it } from 'vitest';

import { effectiveSkin, parseStoredSkin } from './skin';

describe('parseStoredSkin', () => {
  it('reads the two known skins', () => {
    expect(parseStoredSkin('instrument')).toBe('instrument');
    expect(parseStoredSkin('frosted')).toBe('frosted');
  });

  it('defaults to Instrument for missing or unknown values', () => {
    expect(parseStoredSkin(null)).toBe('instrument');
    expect(parseStoredSkin('glass')).toBe('instrument');
  });
});

describe('effectiveSkin', () => {
  const full = { reducedTransparency: false, backdropFilter: true };

  it('keeps the chosen skin when glass can render', () => {
    expect(effectiveSkin('frosted', full)).toBe('frosted');
    expect(effectiveSkin('instrument', full)).toBe('instrument');
  });

  it('falls back to Instrument when the system reduces transparency', () => {
    expect(effectiveSkin('frosted', { ...full, reducedTransparency: true })).toBe('instrument');
  });

  it('falls back to Instrument without backdrop-filter support', () => {
    expect(effectiveSkin('frosted', { ...full, backdropFilter: false })).toBe('instrument');
  });
});

import { describe, expect, it } from 'vitest';

import { OWNER_OPTIONS, objectTypeLabel, ownerCodeFor, ownerName } from './catalog';

describe('ownerName', () => {
  it('names known SATCAT owner codes', () => {
    expect(ownerName('GER')).toBe('Germany');
    expect(ownerName('PRC')).toBe('China');
    expect(ownerName('ESA')).toBe('European Space Agency');
  });

  it('accepts lower-case codes', () => {
    expect(ownerName('us')).toBe('United States');
  });

  it('returns unknown codes unchanged', () => {
    expect(ownerName('DEMO')).toBe('DEMO');
  });
});

describe('ownerCodeFor', () => {
  it('finds a code from a name or a code, ignoring case and spaces', () => {
    expect(ownerCodeFor('Germany')).toBe('GER');
    expect(ownerCodeFor('  germany ')).toBe('GER');
    expect(ownerCodeFor('jpn')).toBe('JPN');
  });

  it('returns null for empty or unknown input', () => {
    expect(ownerCodeFor('')).toBeNull();
    expect(ownerCodeFor('Atlantis')).toBeNull();
  });
});

describe('OWNER_OPTIONS', () => {
  it('is sorted by name', () => {
    const names = OWNER_OPTIONS.map((option) => option.name);
    expect(names).toEqual([...names].sort((a, b) => a.localeCompare(b, 'en')));
  });
});

describe('objectTypeLabel', () => {
  it('turns SATCAT object types into sentence-case words', () => {
    expect(objectTypeLabel('PAY')).toBe('payload');
    expect(objectTypeLabel('R/B')).toBe('rocket body');
    expect(objectTypeLabel('DEB')).toBe('debris');
  });

  it('returns unknown types unchanged', () => {
    expect(objectTypeLabel('TBA')).toBe('TBA');
  });
});

import { describe, expect, it } from 'vitest';

import {
  defaultLayout,
  KEY_STEP_LARGE_PX,
  KEY_STEP_PX,
  maxSizePx,
  parseStoredLayout,
  serializeLayout,
  splitterKeyAction,
  TILE_LIMITS,
  type SplitterKeyContext,
} from './layout';

describe('defaultLayout', () => {
  it('uses the spec defaults, all expanded', () => {
    const layout = defaultLayout();
    expect(layout.left).toEqual({ sizePx: 280, collapsed: false });
    expect(layout.right).toEqual({ sizePx: 320, collapsed: false });
    expect(layout.groups).toEqual({ sizePx: 220, collapsed: false });
    expect(layout.timeline).toEqual({ sizePx: 88, collapsed: false });
    expect(layout.passes).toEqual({ sizePx: 200, collapsed: false });
  });
});

describe('parseStoredLayout', () => {
  it('round-trips a saved layout', () => {
    const layout = defaultLayout();
    layout.left = { sizePx: 360, collapsed: false };
    layout.timeline = { sizePx: 120, collapsed: true };
    expect(parseStoredLayout(serializeLayout(layout))).toEqual(layout);
  });

  it.each([
    ['nothing saved', null],
    ['invalid JSON', '{not json'],
    ['an array', '[]'],
    ['an older version', JSON.stringify({ version: 0, tiles: {} })],
    ['missing tiles', JSON.stringify({ version: 1 })],
  ])('falls back to the defaults for %s', (_, raw) => {
    expect(parseStoredLayout(raw)).toEqual(defaultLayout());
  });

  it('replaces only the tiles whose saved values are outside the limits', () => {
    const raw = JSON.stringify({
      version: 1,
      tiles: {
        left: { sizePx: 150, collapsed: false }, // below the 200 px minimum
        right: { sizePx: 500, collapsed: false }, // above the 460 px maximum
        groups: { sizePx: 140.5, collapsed: false }, // not whole pixels
        timeline: { sizePx: 100, collapsed: 'yes' }, // collapsed is not a boolean
        passes: { sizePx: 150, collapsed: true },
      },
    });
    const layout = parseStoredLayout(raw);
    expect(layout.left).toEqual({ sizePx: 280, collapsed: false });
    expect(layout.right).toEqual({ sizePx: 320, collapsed: false });
    expect(layout.groups).toEqual({ sizePx: 220, collapsed: false });
    expect(layout.timeline).toEqual({ sizePx: 88, collapsed: false });
    expect(layout.passes).toEqual({ sizePx: 150, collapsed: true });
  });

  it('accepts sizes exactly at the limits', () => {
    const raw = JSON.stringify({
      version: 1,
      tiles: { left: { sizePx: 200, collapsed: false }, right: { sizePx: 460, collapsed: false } },
    });
    const layout = parseStoredLayout(raw);
    expect(layout.left.sizePx).toBe(200);
    expect(layout.right.sizePx).toBe(460);
  });
});

describe('maxSizePx', () => {
  it('returns pixel maxima as they are', () => {
    expect(maxSizePx('timeline', 900)).toBe(280);
  });

  it('resolves percentage maxima against the column size', () => {
    expect(maxSizePx('groups', 800)).toBe(480);
    expect(maxSizePx('passes', 845)).toBe(507);
  });
});

describe('splitterKeyAction', () => {
  const column: SplitterKeyContext = {
    orientation: 'vertical',
    grows: 1,
    currentPx: 280,
    minPx: TILE_LIMITS.left.minPx,
    maxPx: 420,
  };

  it('steps 8 px with an arrow and 32 px with Shift', () => {
    expect(splitterKeyAction('ArrowRight', false, column)).toEqual({
      kind: 'resize',
      sizePx: 280 + KEY_STEP_PX,
    });
    expect(splitterKeyAction('ArrowLeft', true, column)).toEqual({
      kind: 'resize',
      sizePx: 280 - KEY_STEP_LARGE_PX,
    });
  });

  it('shrinks a tile on the far side of the splitter when the splitter moves towards it', () => {
    const timeline: SplitterKeyContext = {
      orientation: 'horizontal',
      grows: -1,
      currentPx: 88,
      minPx: 56,
      maxPx: 280,
    };
    expect(splitterKeyAction('ArrowDown', false, timeline)).toEqual({ kind: 'resize', sizePx: 80 });
    expect(splitterKeyAction('ArrowUp', false, timeline)).toEqual({ kind: 'resize', sizePx: 96 });
  });

  it('clamps to the minimum and maximum', () => {
    expect(splitterKeyAction('ArrowLeft', true, { ...column, currentPx: 210 })).toEqual({
      kind: 'resize',
      sizePx: 200,
    });
    expect(splitterKeyAction('ArrowRight', true, { ...column, currentPx: 410 })).toEqual({
      kind: 'resize',
      sizePx: 420,
    });
  });

  it('jumps to the minimum with Home and the maximum with End', () => {
    expect(splitterKeyAction('Home', false, column)).toEqual({ kind: 'resize', sizePx: 200 });
    expect(splitterKeyAction('End', false, column)).toEqual({ kind: 'resize', sizePx: 420 });
  });

  it('toggles collapse with Enter', () => {
    expect(splitterKeyAction('Enter', false, column)).toEqual({ kind: 'toggle-collapse' });
  });

  it('ignores arrows across the splitter and other keys', () => {
    expect(splitterKeyAction('ArrowUp', false, column)).toEqual({ kind: 'ignore' });
    expect(splitterKeyAction('a', false, column)).toEqual({ kind: 'ignore' });
  });
});

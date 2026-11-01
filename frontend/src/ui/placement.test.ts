import { describe, expect, it } from 'vitest';

import { BASE_FIELD_OF_VIEW_RAD, fieldOfViewFor, globeCanvasRect } from './placement';

const WINDOW = { width: 1440, height: 900 };
const TILE = { left: 338, top: 6, width: 770, height: 794 };

describe('globeCanvasRect', () => {
  it('covers exactly the viewport tile in the Instrument skin', () => {
    expect(globeCanvasRect('instrument', TILE, WINDOW)).toEqual(TILE);
  });

  it('covers the whole window, centred on the tile, in the Frosted skin', () => {
    const rect = globeCanvasRect('frosted', TILE, WINDOW);
    const tileCentre = { x: TILE.left + TILE.width / 2, y: TILE.top + TILE.height / 2 };
    expect(rect.left + rect.width / 2).toBe(tileCentre.x);
    expect(rect.top + rect.height / 2).toBe(tileCentre.y);
    expect(rect.left).toBeLessThanOrEqual(0);
    expect(rect.top).toBeLessThanOrEqual(0);
    expect(rect.left + rect.width).toBeGreaterThanOrEqual(WINDOW.width);
    expect(rect.top + rect.height).toBeGreaterThanOrEqual(WINDOW.height);
  });

  it('is the window itself when the tile is centred in the window', () => {
    const centred = { left: 220, top: 150, width: 1000, height: 600 };
    expect(globeCanvasRect('frosted', centred, WINDOW)).toEqual({
      left: 0,
      top: 0,
      width: 1440,
      height: 900,
    });
  });

  it('rounds to whole pixels', () => {
    const rect = globeCanvasRect(
      'instrument',
      { left: 10.4, top: 5.6, width: 99.5, height: 50.2 },
      WINDOW,
    );
    expect(rect).toEqual({ left: 10, top: 6, width: 100, height: 50 });
  });
});

describe('fieldOfViewFor', () => {
  it('keeps the default field of view when the canvas is the tile', () => {
    expect(fieldOfViewFor(TILE, TILE)).toBeCloseTo(BASE_FIELD_OF_VIEW_RAD, 10);
  });

  it('widens the field of view so a larger canvas shows the globe at the same size', () => {
    const canvas = globeCanvasRect('frosted', TILE, WINDOW);
    const fov = fieldOfViewFor(TILE, canvas);
    // Same focal length in pixels: half the long side over tan(half the field of view).
    const tileFocal = Math.max(TILE.width, TILE.height) / 2 / Math.tan(BASE_FIELD_OF_VIEW_RAD / 2);
    const canvasFocal = Math.max(canvas.width, canvas.height) / 2 / Math.tan(fov / 2);
    expect(canvasFocal).toBeCloseTo(tileFocal, 6);
    expect(fov).toBeGreaterThan(BASE_FIELD_OF_VIEW_RAD);
  });

  it('falls back to the default for an empty tile', () => {
    expect(fieldOfViewFor({ left: 0, top: 0, width: 0, height: 0 }, TILE)).toBe(
      BASE_FIELD_OF_VIEW_RAD,
    );
  });
});

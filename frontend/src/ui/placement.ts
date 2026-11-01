/**
 * Where the Cesium canvas sits on screen for each skin. Pure geometry; the globe component
 * applies the result whenever the viewport tile or the window changes size.
 */
import type { Skin } from './skin';

export interface Rect {
  left: number;
  top: number;
  width: number;
  height: number;
}

/**
 * Instrument: the canvas covers exactly the viewport tile.
 * Frosted glass: the canvas fills the window (behind every tile) but is centred on the viewport
 * tile, so the globe sits in the tile rather than in the middle of the window. It is made just
 * large enough, around the tile's centre, to cover the whole window; the page clips the rest.
 * This keeps Cesium's projection untouched (no off-centre frustum).
 */
export function globeCanvasRect(
  skin: Skin,
  tile: Rect,
  windowSize: { width: number; height: number },
): Rect {
  if (skin === 'instrument') return roundRect(tile);
  const centreX = tile.left + tile.width / 2;
  const centreY = tile.top + tile.height / 2;
  const halfWidth = Math.max(centreX, windowSize.width - centreX);
  const halfHeight = Math.max(centreY, windowSize.height - centreY);
  return roundRect({
    left: centreX - halfWidth,
    top: centreY - halfHeight,
    width: 2 * halfWidth,
    height: 2 * halfHeight,
  });
}

/** Cesium's default field of view; it spans the longer side of the canvas. */
export const BASE_FIELD_OF_VIEW_RAD = Math.PI / 3;

/**
 * Field of view for a canvas that may be larger than the viewport tile, chosen so the globe has
 * the same on-screen size as if the canvas were exactly the tile: both keep the same focal length
 * in pixels, with the default field of view spanning the tile's longer side.
 */
export function fieldOfViewFor(tile: Rect, canvas: Rect): number {
  const tileLongSide = Math.max(tile.width, tile.height);
  const canvasLongSide = Math.max(canvas.width, canvas.height);
  if (tileLongSide <= 0 || canvasLongSide <= 0) return BASE_FIELD_OF_VIEW_RAD;
  const focalLengthPx = tileLongSide / 2 / Math.tan(BASE_FIELD_OF_VIEW_RAD / 2);
  return 2 * Math.atan(canvasLongSide / 2 / focalLengthPx);
}

function roundRect(rect: Rect): Rect {
  return {
    left: Math.round(rect.left),
    top: Math.round(rect.top),
    width: Math.round(rect.width),
    height: Math.round(rect.height),
  };
}

/**
 * Workspace layout: which tiles can be resized, their limits in pixels, how splitter keys map
 * to sizes, and how the layout is saved between visits. Pure functions; no DOM access.
 */

/** Tiles whose size the user controls; the other tiles take the remaining space. */
export type TileId = 'left' | 'right' | 'groups' | 'timeline' | 'passes';

export const TILE_IDS: readonly TileId[] = ['left', 'right', 'groups', 'timeline', 'passes'];

export interface TileLimits {
  defaultPx: number;
  minPx: number;
  /** Upper bound: pixels, or a percentage of the column the tile sits in (e.g. "60%"). */
  max: number | `${number}%`;
  /** Size after a double-click or Enter on its splitter: 0 hides a column, 32 keeps a header. */
  collapsedPx: number;
}

export const TILE_LIMITS: Record<TileId, TileLimits> = {
  left: { defaultPx: 280, minPx: 200, max: 420, collapsedPx: 0 },
  right: { defaultPx: 320, minPx: 260, max: 460, collapsedPx: 0 },
  groups: { defaultPx: 220, minPx: 96, max: '60%', collapsedPx: 32 },
  timeline: { defaultPx: 88, minPx: 56, max: 280, collapsedPx: 32 },
  passes: { defaultPx: 200, minPx: 72, max: '60%', collapsedPx: 32 },
};

/** The globe viewport never shrinks below this, whatever the splitters do. */
export const VIEWPORT_MIN_WIDTH_PX = 360;
export const VIEWPORT_MIN_HEIGHT_PX = 240;

export const LAYOUT_STORAGE_KEY = 'sattrack.ui.layout.v1';
const LAYOUT_VERSION = 1;
// Percentage limits cannot be checked without the column size; this only rejects nonsense.
const SANE_MAX_PX = 4000;

export interface TileState {
  /** Size in pixels when expanded (kept while the tile is collapsed). */
  sizePx: number;
  collapsed: boolean;
}

export type WorkspaceLayout = Record<TileId, TileState>;

export function defaultLayout(): WorkspaceLayout {
  const entries = TILE_IDS.map((id) => [
    id,
    { sizePx: TILE_LIMITS[id].defaultPx, collapsed: false },
  ]);
  return Object.fromEntries(entries) as WorkspaceLayout;
}

export function serializeLayout(layout: WorkspaceLayout): string {
  return JSON.stringify({ version: LAYOUT_VERSION, tiles: layout });
}

/**
 * Read a saved layout. Anything unreadable, from another version, or outside the current
 * limits falls back to the defaults (per tile, so one bad value does not reset the rest).
 */
export function parseStoredLayout(raw: string | null): WorkspaceLayout {
  const layout = defaultLayout();
  const tiles = storedTiles(raw);
  if (!tiles) return layout;
  for (const id of TILE_IDS) {
    const entry = tiles[id];
    if (isValidTileState(id, entry))
      layout[id] = { sizePx: entry.sizePx, collapsed: entry.collapsed };
  }
  return layout;
}

function storedTiles(raw: string | null): Record<string, unknown> | null {
  if (raw === null) return null;
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!isRecord(data) || data.version !== LAYOUT_VERSION || !isRecord(data.tiles)) return null;
  return data.tiles;
}

function isValidTileState(id: TileId, value: unknown): value is TileState {
  if (!isRecord(value) || typeof value.collapsed !== 'boolean') return false;
  const { sizePx } = value;
  if (typeof sizePx !== 'number' || !Number.isInteger(sizePx)) return false;
  const limits = TILE_LIMITS[id];
  const maxPx = typeof limits.max === 'number' ? limits.max : SANE_MAX_PX;
  return sizePx >= limits.minPx && sizePx <= maxPx;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/** Resolve a tile's maximum to pixels, given the size of the column (or row) it sits in. */
export function maxSizePx(id: TileId, containerPx: number): number {
  const { max } = TILE_LIMITS[id];
  if (typeof max === 'number') return max;
  return Math.floor((Number.parseFloat(max) / 100) * containerPx);
}

// Spec: arrow keys move a splitter 8 px, with Shift 32 px.
export const KEY_STEP_PX = 8;
export const KEY_STEP_LARGE_PX = 32;

export type SplitterKeyAction =
  { kind: 'resize'; sizePx: number } | { kind: 'toggle-collapse' } | { kind: 'ignore' };

export interface SplitterKeyContext {
  /** "vertical" splitters sit between columns and move with Left/Right. */
  orientation: 'vertical' | 'horizontal';
  /** +1 when moving the splitter right/down grows the tile it controls, -1 when it shrinks it. */
  grows: 1 | -1;
  currentPx: number;
  minPx: number;
  maxPx: number;
}

/**
 * What a key press on a splitter does to the tile it controls (WAI-ARIA window splitter):
 * arrows step, Home/End jump to the tile's minimum/maximum, Enter collapses or restores.
 */
export function splitterKeyAction(
  key: string,
  shiftKey: boolean,
  context: SplitterKeyContext,
): SplitterKeyAction {
  if (key === 'Enter') return { kind: 'toggle-collapse' };
  if (key === 'Home') return { kind: 'resize', sizePx: context.minPx };
  if (key === 'End') return { kind: 'resize', sizePx: context.maxPx };
  const direction = arrowDirection(key, context.orientation);
  if (direction === 0) return { kind: 'ignore' };
  const step = shiftKey ? KEY_STEP_LARGE_PX : KEY_STEP_PX;
  const target = context.currentPx + direction * context.grows * step;
  return { kind: 'resize', sizePx: clamp(Math.round(target), context.minPx, context.maxPx) };
}

function arrowDirection(key: string, orientation: 'vertical' | 'horizontal'): -1 | 0 | 1 {
  const [back, forward] =
    orientation === 'vertical' ? ['ArrowLeft', 'ArrowRight'] : ['ArrowUp', 'ArrowDown'];
  if (key === back) return -1;
  if (key === forward) return 1;
  return 0;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

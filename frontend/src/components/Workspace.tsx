import {
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
  type ReactNode,
  type Ref,
  type RefObject,
} from 'react';
import { Group, Panel, type PanelImperativeHandle, type PanelSize } from 'react-resizable-panels';

import {
  LAYOUT_STORAGE_KEY,
  serializeLayout,
  TILE_IDS,
  TILE_LIMITS,
  VIEWPORT_MIN_HEIGHT_PX,
  VIEWPORT_MIN_WIDTH_PX,
  type TileId,
  type WorkspaceLayout,
} from '../ui/layout';
import { writeStorage } from '../ui/storage';
import { CountMotion } from './RollingNumber';
import { Splitter } from './Splitter';

/** Saves are debounced: a drag or a burst of key presses writes once. */
const SAVE_DELAY_MS = 200;
const SEARCH_MIN_PX = 120;
const SELECTED_MIN_PX = 120;

export interface WorkspaceTiles {
  groups: ReactNode;
  search: ReactNode;
  viewport: ReactNode;
  timeline: ReactNode;
  selected: ReactNode;
  passes: ReactNode;
}

/** Tiles the dock can bring into view. */
export type RevealTarget = 'groups' | 'search' | 'timeline' | 'selected';

export interface WorkspaceHandle {
  /** Expand whatever hides the target tile (its column, or the tile itself). */
  reveal: (target: RevealTarget) => void;
}

interface WorkspaceProps {
  tiles: WorkspaceTiles;
  initialLayout: WorkspaceLayout;
  /** Medium screens show the right column as a sheet instead (see App). */
  withRightColumn: boolean;
  /** Called whenever tiles move or resize, also during a drag. */
  onLayoutChange: () => void;
  ref?: Ref<WorkspaceHandle>;
}

type PanelRefs = Record<TileId, RefObject<PanelImperativeHandle | null>>;

/**
 * The resizable tile grid: three columns, each split in two, with 6 px splitters between them.
 * Pixel limits come from ``TILE_LIMITS``; the globe viewport keeps its minimum size.
 */
export function Workspace({
  tiles,
  initialLayout,
  withRightColumn,
  onLayoutChange,
  ref,
}: WorkspaceProps) {
  const panelRefs: PanelRefs = {
    left: useRef<PanelImperativeHandle>(null),
    right: useRef<PanelImperativeHandle>(null),
    groups: useRef<PanelImperativeHandle>(null),
    timeline: useRef<PanelImperativeHandle>(null),
    passes: useRef<PanelImperativeHandle>(null),
  };
  const sizes = useTileSizes(initialLayout);
  const saveLayout = useLayoutSaving(panelRefs, initialLayout);

  // Restore collapsed tiles once, after the panels mount at their saved expanded sizes, so
  // expanding them later returns to that size.
  const initialRef = useRef(initialLayout);
  const refsRef = useRef(panelRefs);
  useEffect(() => {
    for (const id of TILE_IDS) {
      if (initialRef.current[id].collapsed) refsRef.current[id].current?.collapse();
    }
  }, []);

  // Collapse and expand are instant: the library measures panels in pixels, so animating their
  // size with CSS would make it pin a half-animated size.
  const toggleCollapse = useCallback((tile: TileId) => {
    const panel = refsRef.current[tile].current;
    if (!panel) return;
    if (panel.isCollapsed()) panel.expand();
    else panel.collapse();
  }, []);

  useImperativeHandle(
    ref,
    () => ({
      reveal: (target) => {
        for (const tile of tilesToExpand(target)) refsRef.current[tile].current?.expand();
      },
    }),
    [],
  );

  const onLayoutChanged = () => {
    saveLayout();
    onLayoutChange();
  };
  // Counts in a collapsed tile change out of sight, so they are set without rolling.
  const expanded = (tile: TileId) => sizes.values[tile] > TILE_LIMITS[tile].collapsedPx + 0.5;
  const splitter = (
    tile: TileId,
    label: string,
    orientation: 'vertical' | 'horizontal',
    grows: 1 | -1,
  ) => (
    <Splitter
      label={label}
      tile={tile}
      panelRef={panelRefs[tile]}
      orientation={orientation}
      grows={grows}
      sizePx={sizes.values[tile]}
      onToggleCollapse={() => {
        toggleCollapse(tile);
      }}
    />
  );
  const tilePanel = (tile: TileId) => ({
    id: tile,
    panelRef: panelRefs[tile],
    defaultSize: initialLayout[tile].sizePx,
    minSize: TILE_LIMITS[tile].minPx,
    maxSize: TILE_LIMITS[tile].max,
    collapsible: true,
    collapsedSize: TILE_LIMITS[tile].collapsedPx,
    groupResizeBehavior: 'preserve-pixel-size' as const,
    onResize: sizes.onResize(tile),
  });

  return (
    <Group
      id="columns"
      className="workspace"
      onLayoutChange={onLayoutChange}
      onLayoutChanged={onLayoutChanged}
    >
      <Panel {...tilePanel('left')}>
        <Group
          id="left-column"
          orientation="vertical"
          onLayoutChange={onLayoutChange}
          onLayoutChanged={onLayoutChanged}
        >
          <Panel {...tilePanel('groups')}>
            <CountMotion value={expanded('left') && expanded('groups')}>{tiles.groups}</CountMotion>
          </Panel>
          {splitter('groups', 'Resize groups panel', 'horizontal', 1)}
          <Panel id="search" minSize={SEARCH_MIN_PX}>
            <CountMotion value={expanded('left')}>{tiles.search}</CountMotion>
          </Panel>
        </Group>
      </Panel>
      {splitter('left', 'Resize left column', 'vertical', 1)}
      <Panel id="center" minSize={VIEWPORT_MIN_WIDTH_PX}>
        <Group
          id="center-column"
          orientation="vertical"
          onLayoutChange={onLayoutChange}
          onLayoutChanged={onLayoutChanged}
        >
          <Panel id="viewport" minSize={VIEWPORT_MIN_HEIGHT_PX}>
            {tiles.viewport}
          </Panel>
          {splitter('timeline', 'Resize timeline panel', 'horizontal', -1)}
          <Panel {...tilePanel('timeline')}>{tiles.timeline}</Panel>
        </Group>
      </Panel>
      {withRightColumn && splitter('right', 'Resize right column', 'vertical', -1)}
      {withRightColumn && (
        <Panel {...tilePanel('right')}>
          <Group
            id="right-column"
            orientation="vertical"
            onLayoutChange={onLayoutChange}
            onLayoutChanged={onLayoutChanged}
          >
            <Panel id="selected" minSize={SELECTED_MIN_PX}>
              {tiles.selected}
            </Panel>
            {splitter('passes', 'Resize next passes panel', 'horizontal', -1)}
            <Panel {...tilePanel('passes')}>{tiles.passes}</Panel>
          </Group>
        </Panel>
      )}
    </Group>
  );
}

function tilesToExpand(target: RevealTarget): TileId[] {
  switch (target) {
    case 'groups':
      return ['left', 'groups'];
    case 'search':
      return ['left'];
    case 'timeline':
      return ['timeline'];
    case 'selected':
      return ['right'];
  }
}

/** Current pixel size of each resizable tile, for the splitters' accessible values. */
function useTileSizes(initialLayout: WorkspaceLayout) {
  const [values, setValues] = useState<Record<TileId, number>>(() => {
    const entries = TILE_IDS.map((id) => [id, initialLayout[id].sizePx]);
    return Object.fromEntries(entries) as Record<TileId, number>;
  });
  const onResize = useCallback(
    (tile: TileId) => (size: PanelSize) => {
      setValues((current) =>
        current[tile] === size.inPixels ? current : { ...current, [tile]: size.inPixels },
      );
    },
    [],
  );
  return { values, onResize };
}

/**
 * Save every resizable tile's size and collapsed state, debounced. A collapsed tile keeps the
 * size it had before collapsing; tiles not on screen (e.g. the right column on medium screens)
 * keep their saved values.
 */
function useLayoutSaving(panelRefs: PanelRefs, initialLayout: WorkspaceLayout): () => void {
  const savedRef = useRef<WorkspaceLayout>(structuredClone(initialLayout));
  const refsRef = useRef(panelRefs);
  const timerRef = useRef<number | undefined>(undefined);

  useEffect(
    () => () => {
      window.clearTimeout(timerRef.current);
    },
    [],
  );

  return useCallback(() => {
    window.clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(() => {
      const layout = savedRef.current;
      for (const id of TILE_IDS) {
        const panel = refsRef.current[id].current;
        if (!panel) continue;
        const collapsed = panel.isCollapsed();
        const sizePx = collapsed ? layout[id].sizePx : Math.round(panel.getSize().inPixels);
        layout[id] = { sizePx: Math.max(sizePx, TILE_LIMITS[id].minPx), collapsed };
      }
      writeStorage(LAYOUT_STORAGE_KEY, serializeLayout(layout));
    }, SAVE_DELAY_MS);
  }, []);
}

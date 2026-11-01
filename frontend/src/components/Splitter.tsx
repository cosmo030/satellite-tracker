import { useEffect, useRef, type RefObject } from 'react';
import { Separator, type PanelImperativeHandle } from 'react-resizable-panels';

import { maxSizePx, splitterKeyAction, TILE_LIMITS, type TileId } from '../ui/layout';

interface SplitterProps {
  /** Accessible name, e.g. "Resize search panel". */
  label: string;
  /** The tile this splitter sizes (its "primary pane" in WAI-ARIA terms). */
  tile: TileId;
  panelRef: RefObject<PanelImperativeHandle | null>;
  /** "vertical" splitters sit between columns. */
  orientation: 'vertical' | 'horizontal';
  /** +1 when moving the splitter right/down grows the tile, -1 when it shrinks it. */
  grows: 1 | -1;
  /** Current size of the tile in pixels, announced by screen readers. */
  sizePx: number;
  onToggleCollapse: () => void;
}

/**
 * A 6 px gutter that resizes one tile. The library handles pointer and touch dragging; this
 * component replaces its keyboard steps (percentages) and double-click (reset) with the spec's:
 * arrows 8 px, Shift 32 px, Home/End to the tile's limits, Enter and double-click collapse.
 */
export function Splitter({
  label,
  tile,
  panelRef,
  orientation,
  grows,
  sizePx,
  onToggleCollapse,
}: SplitterProps) {
  const elementRef = useRef<HTMLDivElement>(null);
  const toggleRef = useRef(onToggleCollapse);

  useEffect(() => {
    toggleRef.current = onToggleCollapse;
  }, [onToggleCollapse]);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;
    // Capture phase: runs before the library's own listener on the same element, which skips
    // events that were already handled (defaultPrevented).
    const onKeyDown = (event: KeyboardEvent) => {
      const panel = panelRef.current;
      if (!panel) return;
      const { inPixels, asPercentage } = panel.getSize();
      const containerPx = asPercentage > 0 ? (inPixels * 100) / asPercentage : 0;
      const action = splitterKeyAction(event.key, event.shiftKey, {
        orientation,
        grows,
        currentPx: inPixels,
        minPx: TILE_LIMITS[tile].minPx,
        maxPx: Math.max(TILE_LIMITS[tile].minPx, maxSizePx(tile, containerPx)),
      });
      if (action.kind === 'ignore') return;
      event.preventDefault();
      if (action.kind === 'toggle-collapse') toggleRef.current();
      else panel.resize(action.sizePx);
    };
    element.addEventListener('keydown', onKeyDown, { capture: true });
    return () => {
      element.removeEventListener('keydown', onKeyDown, { capture: true });
    };
  }, [panelRef, tile, orientation, grows]);

  return (
    <Separator
      elementRef={elementRef}
      className="splitter"
      aria-label={label}
      aria-valuetext={`${Math.round(sizePx)} pixels`}
      disableDoubleClick
      onDoubleClick={onToggleCollapse}
    />
  );
}

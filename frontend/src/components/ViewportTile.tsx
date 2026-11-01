import { useEffect, useRef, useState, type Ref } from 'react';

import type { GlobeLayers } from '../globe/GlobeScene';
import { LayersIcon, SunIcon } from './icons';
import { RollingNumber } from './RollingNumber';

interface ViewportTileProps {
  /** The globe follows this element's position and size. */
  tileRef: Ref<HTMLElement>;
  groupName: string | null;
  satelliteCount: number | null;
  lighting: boolean;
  onToggleLighting: () => void;
  layers: GlobeLayers;
  onChangeLayers: (layers: GlobeLayers) => void;
}

/** Transparent window onto the globe, with the group chip and globe toggles on top. */
export function ViewportTile({
  tileRef,
  groupName,
  satelliteCount,
  lighting,
  onToggleLighting,
  layers,
  onChangeLayers,
}: ViewportTileProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <section ref={tileRef} className="tile viewport" aria-labelledby="viewport-heading">
      <h2 id="viewport-heading" className="visually-hidden">
        Globe
      </h2>
      <div className="viewport-overlay">
        <span className="chip overlay-chip">
          <GroupLabel groupName={groupName} count={satelliteCount} />
        </span>
        <div className="viewport-tools">
          <button
            type="button"
            className="chip overlay-chip"
            aria-label="Globe layers"
            aria-expanded={menuOpen}
            onClick={() => {
              setMenuOpen((open) => !open);
            }}
          >
            <LayersIcon />
          </button>
          <button
            type="button"
            className="chip overlay-chip"
            aria-label="Day and night lighting"
            aria-pressed={lighting}
            onClick={onToggleLighting}
          >
            <SunIcon />
          </button>
          {menuOpen && (
            <LayersMenu
              layers={layers}
              onChange={onChangeLayers}
              onClose={() => {
                setMenuOpen(false);
              }}
            />
          )}
        </div>
      </div>
    </section>
  );
}

function GroupLabel({ groupName, count }: { groupName: string | null; count: number | null }) {
  if (!groupName) return <>No group selected</>;
  if (count === null) return <>{groupName}, loading…</>;
  // Keyed by group: switching groups shows the new count at once instead of rolling to it.
  return (
    <>
      {groupName}, <RollingNumber key={groupName} value={count} />
    </>
  );
}

interface LayersMenuProps {
  layers: GlobeLayers;
  onChange: (layers: GlobeLayers) => void;
  onClose: () => void;
}

const LAYER_LABELS: Record<keyof GlobeLayers, string> = {
  orbitPath: 'Orbit path',
  groundTrack: 'Ground track',
};

function LayersMenu({ layers, onChange, onClose }: LayersMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);

  // Close on a click outside the menu (the toggle button handles its own clicks) or on Escape.
  useEffect(() => {
    const onPointerDown = (event: PointerEvent) => {
      const menu = menuRef.current;
      const toggle = menu?.parentElement;
      if (event.target instanceof Node && !toggle?.contains(event.target)) onClose();
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [onClose]);

  return (
    <div ref={menuRef} className="popover layers-menu" role="group" aria-label="Globe layers">
      {(Object.keys(LAYER_LABELS) as (keyof GlobeLayers)[]).map((key) => (
        <button
          key={key}
          type="button"
          role="switch"
          className="switch"
          aria-checked={layers[key]}
          onClick={() => {
            onChange({ ...layers, [key]: !layers[key] });
          }}
        >
          <span className="switch-track" aria-hidden="true" />
          {LAYER_LABELS[key]}
        </button>
      ))}
    </div>
  );
}

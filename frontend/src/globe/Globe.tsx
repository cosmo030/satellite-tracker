import { useEffect, useImperativeHandle, useRef, type Ref, type RefObject } from 'react';

import type { GeoPosition } from '../orbit/propagation';
import { fieldOfViewFor, globeCanvasRect } from '../ui/placement';
import type { Skin } from '../ui/skin';
import { GlobeScene, type GlobeLayers } from './GlobeScene';

export interface GlobeHandle {
  /** Fly the camera back to the default view of the whole Earth. */
  flyHome: () => void;
  /** Re-read the viewport tile's position (it can move without changing size). */
  updatePlacement: () => void;
}

interface GlobeProps {
  noradIds: readonly number[];
  positions: Float64Array | null;
  selectedId: number | null;
  selectedPosition: GeoPosition | null;
  selectedTrack: readonly GeoPosition[];
  onPick: (noradId: number | null) => void;
  /** The viewport tile the globe is placed in (or centred on, in the Frosted skin). */
  viewportTile: HTMLElement | null;
  skin: Skin;
  lighting: boolean;
  layers: GlobeLayers;
  now: Date;
  ref?: Ref<GlobeHandle>;
}

/**
 * Mounts one Cesium scene underneath the workspace and keeps it placed on the viewport tile.
 * The viewer is created once; skins and splitter drags only move or resize its container.
 */
export function Globe({
  noradIds,
  positions,
  selectedId,
  selectedPosition,
  selectedTrack,
  onPick,
  viewportTile,
  skin,
  lighting,
  layers,
  now,
  ref,
}: GlobeProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const creditsRef = useRef<HTMLDivElement>(null);
  const cesiumCreditsRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<GlobeScene | null>(null);
  const onPickRef = useRef(onPick);

  useEffect(() => {
    onPickRef.current = onPick;
  }, [onPick]);

  useEffect(() => {
    if (!hostRef.current || !cesiumCreditsRef.current) return;
    const scene = new GlobeScene(hostRef.current, cesiumCreditsRef.current, (id) => {
      onPickRef.current(id);
    });
    sceneRef.current = scene;
    return () => {
      scene.destroy();
      sceneRef.current = null;
    };
  }, []);

  const placeRef = useGlobePlacement(viewportTile, skin, { hostRef, creditsRef, sceneRef });
  useImperativeHandle(
    ref,
    () => ({
      flyHome: () => sceneRef.current?.flyHome(),
      updatePlacement: () => {
        placeRef.current();
      },
    }),
    [placeRef],
  );

  useEffect(() => {
    sceneRef.current?.setSatellites(noradIds);
  }, [noradIds]);

  useEffect(() => {
    if (positions) sceneRef.current?.updatePositions(positions);
  }, [positions]);

  useEffect(() => {
    sceneRef.current?.setSelectedPosition(selectedId, selectedPosition);
  }, [selectedId, selectedPosition]);

  useEffect(() => {
    sceneRef.current?.setSelectedTrack(selectedTrack);
  }, [selectedTrack]);

  useEffect(() => {
    // The skin's accent lives in CSS; <html data-skin> is set in a layout effect, before this runs.
    const accent = getComputedStyle(document.documentElement).getPropertyValue('--accent');
    sceneRef.current?.setAccent(accent);
  }, [skin]);

  useEffect(() => {
    sceneRef.current?.setLighting(lighting);
  }, [lighting]);

  useEffect(() => {
    sceneRef.current?.setLayers(layers);
  }, [layers]);

  useEffect(() => {
    sceneRef.current?.setTime(now);
  }, [now]);

  return (
    <div className="globe-stage">
      <div ref={hostRef} className="globe-host" aria-label="3D globe with satellite positions" />
      <div ref={creditsRef} className="globe-credits">
        <div ref={cesiumCreditsRef} />
        <a href="https://celestrak.org">Orbital data: CelesTrak</a>
      </div>
    </div>
  );
}

/**
 * Keep the canvas on the viewport tile (Instrument) or full-bleed around it (Frosted).
 * Returns a ref to the placement function so callers can re-run it after a layout change.
 */
function useGlobePlacement(
  tile: HTMLElement | null,
  skin: Skin,
  { hostRef, creditsRef, sceneRef }: PlacementRefs,
): RefObject<() => void> {
  const placeRef = useRef<() => void>(() => undefined);
  useEffect(() => {
    const host = hostRef.current;
    const credits = creditsRef.current;
    if (!tile || !host || !credits) return;
    const place = () => {
      const bounds = tile.getBoundingClientRect();
      const rect = globeCanvasRect(skin, bounds, {
        width: window.innerWidth,
        height: window.innerHeight,
      });
      // A canvas larger than the tile (Frosted) keeps the globe at the tile's scale.
      sceneRef.current?.setFieldOfView(fieldOfViewFor(bounds, rect));
      host.style.left = `${rect.left}px`;
      host.style.top = `${rect.top}px`;
      host.style.width = `${rect.width}px`;
      host.style.height = `${rect.height}px`;
      credits.style.left = `${Math.round(bounds.left)}px`;
      credits.style.top = `${Math.round(bounds.bottom)}px`;
    };
    place();
    placeRef.current = place;
    // ResizeObserver callbacks run after layout and before paint, so the globe never lags a drag.
    const observer = new ResizeObserver(place);
    observer.observe(tile);
    window.addEventListener('resize', place);
    return () => {
      placeRef.current = () => undefined;
      observer.disconnect();
      window.removeEventListener('resize', place);
    };
  }, [tile, skin, hostRef, creditsRef, sceneRef]);
  return placeRef;
}

interface PlacementRefs {
  hostRef: RefObject<HTMLDivElement | null>;
  creditsRef: RefObject<HTMLDivElement | null>;
  sceneRef: RefObject<GlobeScene | null>;
}

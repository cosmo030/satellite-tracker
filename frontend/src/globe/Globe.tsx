import { useEffect, useRef } from 'react';

import type { GeoPosition } from '../orbit/propagation';
import { GlobeScene } from './GlobeScene';

interface GlobeProps {
  noradIds: readonly number[];
  positions: Float64Array | null;
  selectedId: number | null;
  selectedPosition: GeoPosition | null;
  selectedTrack: readonly GeoPosition[];
  onPick: (noradId: number | null) => void;
}

/** React wrapper that mounts one Cesium scene and forwards prop changes to it. */
export function Globe({
  noradIds,
  positions,
  selectedId,
  selectedPosition,
  selectedTrack,
  onPick,
}: GlobeProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<GlobeScene | null>(null);
  const onPickRef = useRef(onPick);

  useEffect(() => {
    onPickRef.current = onPick;
  }, [onPick]);

  useEffect(() => {
    if (!containerRef.current) return;
    const scene = new GlobeScene(containerRef.current, (id) => {
      onPickRef.current(id);
    });
    sceneRef.current = scene;
    return () => {
      scene.destroy();
      sceneRef.current = null;
    };
  }, []);

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

  return (
    <div ref={containerRef} className="globe" aria-label="3D globe with satellite positions" />
  );
}
